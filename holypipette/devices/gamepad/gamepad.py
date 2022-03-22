'''
Gamepad reader

- left_trigger + right_trigger
- Save angles in config file.

DONE:
- Joysticks -> (angle, intensity) -> map intensity (e.g. threshold and power law)
- Configuration file: check if file has been modified (date changed?), or simply reload every second.
- Each key maps to method.
- Get key combinations; buttons must be switches
- Events triggered by buttons?
    If there is a combination A+B, then A should trigger an event when off.
    So if A+B triggers the event when off, we'll have a sequence like:
        A, A+B, A, none
    and the event A+B should be triggered.
    So the algorithm is:
        - wait until there is an off event.
        - trigger the (possibly combination) event.
        - wait until all buttons are off.
- Events should be put in a queue (with pop?), because we don't want to have conflicting commands.
    unless there is just a main loop dealing with the current state, and events directly trigger a command.
    It doesn't even need to be a thread. We make a thread and join.
- Duration is measured relative to the last on. If above some threshold (1 s?), then it's a long event.
- Withdraw should move in if withdrawn, but it should also stop when released, so it's a different kind of event.

TODO:
- sort combinations defined in configuration file
- Maybe display image of XBox One with commands.
'''
import threading
import time
import yaml
import inputs
import os

__all__ = ['GamepadReader', 'GamepadProcessor']

button_events = {'BTN_WEST': 'X',
                 'BTN_NORTH': 'Y',
                 'BTN_EAST': 'B',
                 'BTN_SOUTH': 'A',
                 'select': 'select', # I don't know the keys for those ones
                 'menu': 'menu',
                 'left_finger_button': 'left_finger_button',
                 'right_finger_button': 'right_finger_button'
                }

long_duration_threshold = 1. # in seconds

class GamepadReader(threading.Thread):
    '''
    Captures gamepad input and puts events in queue.
    '''
    def __init__(self, gamepad_number=0):
        self.gamepad = inputs.devices.gamepads[gamepad_number]
        super(GamepadReader, self).__init__()
        self.terminated = False
        self.queue = []

    def run(self):
        while not self.terminated:
            self.queue.append(self.gamepad.read()[0])  # This blocks the thread
            if True:
                print(self.queue[-1])

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
        # Buttons
        self.X = False
        self.Y = False
        self.A = False
        self.B = False
        self.select = False
        self.menu = False
        self.left_finger = False
        self.right_finger = False

        ## Transformed joystick variables
        self.LX_processed = 0.
        self.LY_processed = 0.
        self.RX_processed = 0.
        self.RY_processed = 0.
        self.Z_processed = 0.

        ## Buttons
        self.button = dict.fromkeys(list(button_events.values()), False)
        self.time_last_on = None

        ## Parameters
        self.joystick_threshold = self.config.get('joystick_threshold', .1)
        self.joystick_power = self.config.get('joystick_power', 3)

        self.releasing = False # if True, in a releasing process: do not process further events

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

    def process_joysticks(self):
        '''
        Processes joystick states.
        Then call the relevant methods (left, right, cross).
        '''
        # Process joystick states
        self.Z_processed = self.map_joystick(self.RZ - self.LZ)

        intensity = (self.LX**2 + self.LY**2)**.5
        unit_X, unit_Y = self.LX/intensity, self.LY/intensity
        mapped_intensity = self.map_joystick(intensity)
        self.LX_processed, self.LY_processed = mapped_intensity*unit_X, mapped_intensity*unit_Y

        intensity = (self.RX**2 + self.RY**2)**.5
        unit_X, unit_Y = self.RX/intensity, self.RY/intensity
        mapped_intensity = self.map_joystick(intensity)
        self.RX_processed, self.RY_processed = mapped_intensity*unit_X, mapped_intensity*unit_Y

        # Call the relevant methods
        self.command('left', self.LX_processed, self.LY_processed)
        self.command('right', self.RX_processed, self.RY_processed)
        self.command('cross', self.crossX, self.crossY)
        self.command('trigger', self.Z_processed)

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

    def check_config(self):
        '''
        Checks if the config file has been modified, and if so reloads it.
        '''
        try:
            if self.config_last_modified != os.stat(self.config_file)[8]:
                self.load(self.config_file)
                print('modified')
        except FileNotFoundError: # possibly being written
            time.sleep(.1)

    def run(self):
        while not self.terminated:
            while self.gamepad != []:
                event = self.gamepad.pop()
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
                        if (combination+' ON') in self.config:
                            self.command(combination+' ON')
                        self.releasing = False
                    elif not self.releasing: # OFF event
                        duration = time.time() - self.time_last_on
                        long_event = (duration>long_duration_threshold)
                        combination = self.get_combination()
                        # Trigger an OFF event
                        if (combination+' OFF') in self.config:
                            if not long_event or not self.command('long '+combination + ' OFF'):
                                self.command(combination + ' OFF')
                        else:
                            if not long_event or not self.command('long '+combination):
                                self.command(combination)
                        # Trigger event
                        self.button[button_event] = (event.state==1)
                        self.releasing = True # in a releasing process: do not process further events

            # This could be done only at certain time intervals
            self.process_joysticks()

    def command(self, name, *args):
        '''
        Executes a command.
        If the description is a list, the first item is the command name, the rest are arguments.
        Returns True if executed
        '''
        if name in self.config: # otherwise does nothing
            description = self.config[name]
            if isinstance(description, list):
                command_name = description[0]
                arguments = description[1:]
            else:
                command_name = description
                arguments = []
            try:
                self.__getattribute__(command_name)(*(args+arguments))
            except:
                print('Failed executing', command_name, *(args+arguments))
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
        self.stop() # just a synonym

if __name__ == '__main__':
    reader = GamepadReader()
    reader.start()
    gamepad = GamepadProcessor(reader, config='~/PycharmProjects/holypipette/development/gamepad.yaml')
    gamepad.start()
    gamepad.stop()
    reader.stop()
