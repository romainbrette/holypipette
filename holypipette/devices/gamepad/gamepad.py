'''
Gamepad reader
'''
import threading
import time
import yaml
import inputs
import os
import numpy as np

__all__ = ['GamepadReader', 'GamepadProcessor']

button_events = {'BTN_WEST': 'X',
                 'BTN_NORTH': 'Y',
                 'BTN_EAST': 'B',
                 'BTN_SOUTH': 'A',
                 'BTN_START': 'select', # I don't know the keys for those ones
                 'BTN_SELECT': 'menu',
                 'BTN_TL': 'left_finger_button',
                 'BTN_TR': 'right_finger_button'
                }

all_codes = ['ABS_X', 'ABS_Y', 'ABS_Z', 'ABS_RX', 'ABS_RY', 'ABS_RZ', 'ABS_HAT0X', 'ABS_HAT0Y'] + button_events.keys()

long_duration_threshold = 1. # in seconds

class GamepadReader(threading.Thread):
    '''
    Captures gamepad input and puts events in queue.
    '''
    def __init__(self, gamepad_number=0, id=None):
        self.gamepad = inputs.devices.gamepads[gamepad_number]
        super(GamepadReader, self).__init__()
        self.terminated = False
        self.queue = []
        self.id = id

    def run(self):
        while not self.terminated:
            self.queue.insert(0,self.gamepad.read()[0])  # This blocks the thread
            if False:
                print(self.id ,self.queue[-1].code)

    def stop(self):
        self.terminated = True

class GamepadProcessor(threading.Thread):
    '''
    Captures gamepad input and processes events.
    '''
    def __init__(self, gamepad_reader, config=None):
        self.gamepad = gamepad_reader
        super(GamepadProcessor, self).__init__()
        self.terminated = False

        self.load(config)

        self.last_change = dict.fromkeys(all_codes, time.time())

        ## State variables
        # Joystick 1
        self.LX = 0.
        self.LY = 0.
        # Joystick 2
        self.RX = 0.
        self.RY = 0.
        # Triggers under the fingers
        self.LZ = 0.
        self.RZ = 0.
        # Cross
        self.crossX = 0.
        self.crossY = 0.
        self.previous_crossX = 0.
        self.previous_crossY = 0.
        # Buttons
        # self.X = False
        # self.Y = False
        # self.A = False
        # self.B = False
        # self.select = False
        # self.menu = False
        # self.left_finger = False
        # self.right_finger = False

        ## Transformed joystick variables
        self.LX_processed = 0.
        self.LY_processed = 0.
        self.RX_processed = 0.
        self.RY_processed = 0.
        self.Z_processed = 0.
        self.previous_LX_processed = 0.
        self.previous_LY_processed = 0.
        self.previous_RX_processed = 0.
        self.previous_RY_processed = 0.
        self.previous_Z_processed = 0.

        ## Buttons
        self.button = dict.fromkeys(list(button_events.values()), False)
        self.time_last_on = None

        ## Parameters
        self.joystick_threshold = self.config['parameters'].get('joystick_threshold', .15)
        self.joystick_power = self.config['parameters'].get('joystick_power', 3)
        self.switch_on_duration = self.config['parameters'].get('switch_on_duration', 5.) # to switch to high speed mode
        self.switch_off_duration = self.config['parameters'].get('switch_off_duration', 5.) # to switch to low speed mode

        self.releasing = False # if True, in a releasing process: do not process further events
        self.last_config_checked = time.time()

    def vibrate(self, left, right, duration_ms):
        self.gamepad.set_vibration(left, right, duration_ms) # left and right are between 0 and 1

    def map_joystick(self, x):
        '''
        Maps a signed joystick value according to threshold and power.
        '''
        if abs(x)<self.joystick_threshold:
            return 0.
        sign = 2*(x>0)-1
        #return sign*abs(x)**self.joystick_power
        # this may cause problems if x>1
        return sign*((abs(x)-self.joystick_threshold)/(1-self.joystick_threshold))**self.joystick_power

    def discrete_state4(self, X, Y):
        '''
        Returns discretized position (-1, 0, +1 for each component), 4 cardinal positions
        '''
        Xd = ((X>Y) and (X>-Y)) - ((X<Y) and (X<-Y))
        Yd = ((Y>X) and (Y>-X)) - ((Y<X) and (Y<-X))
        return Xd, Yd

    def discrete_state8(self, X, Y):
        '''
        Returns discretized position (-1, 0, +1 for each component), 8 cardinal positions
        '''
        Xd = ((2*X>Y) and (2*X>-Y)) - ((2*X<Y) and (2*X<-Y))
        Yd = ((2*Y>X) and (2*Y>-X)) - ((2*Y<X) and (2*Y<-X))
        return Xd, Yd

    def process_joysticks(self):
        '''
        Processes joystick states.
        Then call the relevant methods (left, right, cross).
        '''
        # Process joystick states
        self.Z_processed = self.map_joystick(self.RZ - self.LZ)
        #if self.Z_processed != 0.:
        self.command('trigger', self.Z_processed)

        intensity = (self.LX**2 + self.LY**2)**.5
        if intensity>0:
            unit_X, unit_Y = self.LX/intensity, self.LY/intensity
            mapped_intensity = self.map_joystick(intensity)
            self.LX_processed, self.LY_processed = mapped_intensity * unit_X, mapped_intensity * unit_Y
        else:
            self.LX_processed, self.LY_processed = 0., 0.
        self.command('left', self.LX_processed, self.LY_processed)

        intensity = (self.RX**2 + self.RY**2)**.5
        if intensity>0:
            unit_X, unit_Y = self.RX/intensity, self.RY/intensity
            mapped_intensity = self.map_joystick(intensity)
            self.RX_processed, self.RY_processed = mapped_intensity * unit_X, mapped_intensity * unit_Y
        else:
            self.RX_processed, self.RY_processed = 0., 0.
        self.command('right', self.RX_processed, self.RY_processed)

        # Call the relevant methods
        self.command('cross', self.crossX, self.crossY)

        self.previous_LX_processed = self.LX_processed
        self.previous_RX_processed = self.RX_processed
        self.previous_LY_processed = self.LY_processed
        self.previous_RY_processed = self.RY_processed
        self.previous_Z_processed = self.Z_processed
        self.previous_crossX = self.crossX
        self.previous_crossY = self.crossY


    def save(self):
        with open(self.config_file, 'w') as f:
            yaml.safe_dump(self.config, f, default_flow_style=False)
        self.config_last_modified = os.stat(self.config_file)[8]

    def load(self, config=None):
        '''
        Loads the configuration file.
        '''
        if config is None:
            config = '~/gamepad.yaml'
        self.config_file = os.path.expanduser(config)

        with open(self.config_file, 'r') as f:
            self.config = yaml.safe_load(f)

        self.config_last_modified = os.stat(self.config_file)[8]

        self.keys = self.config['keys']
        # Sort configuration keys
        new_keys = {}
        for key, value in self.keys.items():
            new_key = '+'.join(sorted(key.split('+')))
            new_keys[new_key] = value
        self.keys = new_keys

    def check_config(self):
        '''
        Checks if the config file has been modified, and if so reloads it.
        '''
        try:
            if self.config_last_modified != os.stat(self.config_file)[8]:
                self.load(self.config_file)
                print('Configuration modified, reloading')
        except FileNotFoundError: # possibly being written
            time.sleep(.1)

    def run(self):
        while not self.terminated:
            while self.gamepad.queue != []:
                event = self.gamepad.queue.pop()
                self.last_change[event.code] = time.time()
                if event.code == 'ABS_X':
                    self.LX = event.state/32768.
                elif event.code == 'ABS_Y':
                    self.LY = event.state / 32768.
                elif event.code == 'ABS_Z':
                    self.LZ = event.state / 255.
                elif event.code == 'ABS_RX':
                    self.RX = event.state/32768.
                elif event.code == 'ABS_RY':
                    self.RY = event.state / 32768.
                elif event.code == 'ABS_RZ':
                    self.RZ = event.state / 255.
                elif event.code == 'ABS_HAT0X':
                    self.crossX = event.state*1.
                elif event.code == 'ABS_HAT0Y':
                    self.crossY = event.state*1.
                elif event.code in button_events.keys():
                    button_event = button_events[event.code]
                    if event.state == 1: # ON event
                        self.button[button_event] = (event.state == 1)
                        self.time_last_on = time.time()
                        # Trigger an ON event
                        combination = self.get_combination()
                        if (combination+' onset') in self.keys:
                            self.command(combination+' onset')
                        self.releasing = False
                    elif not self.releasing: # OFF event
                        duration = time.time() - self.time_last_on
                        long_event = (duration>long_duration_threshold)
                        combination = self.get_combination()
                        # Trigger an offset event
                        if (combination+' offset') in self.keys:
                            if not long_event or not self.command('long '+combination + ' offset'):
                                self.command(combination + ' offset')
                        else:
                            if not long_event or not self.command('long '+combination):
                                self.command(combination)
                        # Trigger event
                        self.button[button_event] = (event.state==1)
                        self.releasing = True # in a releasing process: do not process further events
                    else:
                        self.button[button_event] = (event.state == 1)

            # This could be done only at certain time intervals

            # Buttons
            combination = self.get_combination()
            if (combination+' on') in self.keys:
                self.command(combination + ' on')
            # Joysticks
            self.process_joysticks()
            time.sleep(.05)

            t = time.time()
            if t-self.last_config_checked>1.:
                self.check_config()
                self.last_config_checked = t

        self.save()

    def command(self, name, *args, **kwds):
        '''
        Executes a command.
        If the description is a list, the first item is the command name, the rest are arguments.
        Returns True if executed
        '''
        if name in self.keys: # otherwise does nothing
            description = self.keys[name]
            if isinstance(description, list):
                command_name = description[0]
                arguments = description[1:]
            else:
                command_name = description
                arguments = []
            self.__getattribute__(command_name)(*(list(args)+list(arguments)), **kwds)
            return True
        else:
            return False

    def get_combination(self):
        '''
        Returns the current button combination.
        '''
        return '+'.join(sorted([button for button in self.button if self.button[button]]))

    def stop(self):
        self.terminated = True

    def quit(self):
        print("Quitting")
        self.stop() # just a synonym

if __name__ == '__main__':
    reader = GamepadReader(id=1)
    reader.start()
    #gamepad = GamepadProcessor(reader, config='~/PycharmProjects/holypipette/development/gamepad.yaml')
    #gamepad.start()
    #gamepad.join()
    reader2 = GamepadReader(id=2)
    reader2.start()
    time.sleep(10)
    reader2.stop()
    reader.stop()
    print([(event.code, event.state) for event in reader.queue])
    print()
    print([(event.code, event.state) for event in reader2.queue])
