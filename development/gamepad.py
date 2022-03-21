'''
Gamepad control of stage and manipulators

Note: we can make it vibrate with
gamepad.set_vibration(0-1,0-1, duration in ms)
'''
import os
import threading
import time

import inputs
import numpy as np

from holypipette.devices.manipulator.luigsneumann_SM10 import LuigsNeumann_SM10

#### COPIED FROM CLAMPY
class GamepadReader(threading.Thread):
    '''
    Captures gamepad input and stores events and current state of buttons.
    This is necessary because reading is in blocking mode. (could this be changed?)
    '''
    def __init__(self, gamepad_number=0):
        self.event_container = []
        self.gamepad = inputs.devices.gamepads[gamepad_number]
        super(GamepadReader, self).__init__()
        self.terminated = False
        # Joystick 1
        self.X = 0.
        self.Y = 0.
        # Joystick 2
        self.RX = 0.
        self.RY = 0.
        # Buttons under the fingers
        self.Z = 0.
        self.RZ = 0.
        # Cross
        self.crossX = 0.
        self.crossY = 0.

    def run(self):
        while not self.terminated:
            event = self.gamepad.read()[0] # This blocks the thread
            if event.code == 'ABS_X':
                self.X = event.state/32768.
            elif event.code == 'ABS_Y':
                self.Y = event.state / 32768.
            elif event.code == 'ABS_Z':
                self.Z = event.state / 255.
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
            else:
                self.event_container.append(event)

    def stop(self):
        self.terminated = True

def run_gamepad(controller, axes):
    running = True
    reader = GamepadReader()
    reader.start()

    low_speed = 1
    high_speed = 2 # could switch to higher speeds with duration

    controller.set_single_step_factor_trackball(axes[0], low_speed)
    controller.set_single_step_factor_trackball(axes[1], low_speed)
    controller.set_single_step_factor_trackball(axes[2], low_speed)

    while running:
        for event in reader.event_container: # maybe pop instead
            if event.code == 'BTN_WEST': # X
                running = False # exit # actually there is an on and off state
            elif event.code != 'SYN_REPORT':
                print(event.code, event.state)
        reader.event_container[:] = []

        # just one threshold : .95
        # then use angle

        intensity = (reader.X**2 + reader.Y**2)**.5

        if abs(reader.X) > .1:
            if intensity<.95:
                controller.set_single_step_factor_trackball(axes[0], low_speed)
            else:
                controller.set_single_step_factor_trackball(axes[0], high_speed)
            controller.single_step_trackball(axes[0], 2*(2*(reader.X>0)-1))
            # if reader.X> 0:
            #     print('moving')
            #     controller.single_step_trackball(axes[0], 1)
            # else:
            #     controller.single_step_trackball(axes[0], -2)
        if abs(reader.Y) > .1:
            if intensity<.95:
                controller.set_single_step_factor_trackball(axes[1], low_speed)
            else:
                controller.set_single_step_factor_trackball(axes[1], high_speed)
            controller.single_step_trackball(axes[1], 2*(2*(reader.Y>0)-1))
            # if reader.Y> 0:
            #     controller.single_step_trackball(axes[1], 1)
            # else:
            #     controller.single_step_trackball(axes[1], -2)

        z = reader.Z - reader.RZ
        if abs(z) > 0.1:
            #z_step = 1 if z > 0 else -2
            if abs(z)<.95:
                controller.set_single_step_factor_trackball(axes[2], low_speed)
            else:
                controller.set_single_step_factor_trackball(axes[2], high_speed)
            controller.single_step_trackball(axes[2], 2*(2*(z>0)-1))
            #controller.single_step_trackball(axes[2], z_step)

        time.sleep(.05)

    reader.stop()

def run_gamepad2(controller, axes):
    running = True
    reader = GamepadReader()
    reader.start()

    low_speed = 1
    high_speed = 20 # could switch to higher speeds with duration
    # need to change velocity too

    while running:
        for event in reader.event_container: # maybe pop instead
            if (event.code == 'BTN_WEST') and (event.state == 1): # X
                running = False # exit # actually there is an on and off state
            elif event.code != 'SYN_REPORT':
                print(event.code, event.state)
        reader.event_container[:] = []

        # just one threshold : .95
        # then use angle

        intensity = (reader.X**2 + reader.Y**2)**.5

        if abs(reader.X) > .1:
            controller.set_single_step_distance(axes[0], reader.X**3*high_speed)
            controller.single_step(axes[0], 1)
            # if intensity<.95:
            #     controller.set_single_step_distance(axes[0], low_speed)
            # else:
            #     controller.set_single_step_distance(axes[0], high_speed)
            #controller.single_step(axes[0], 1*(2*(reader.X>0)-1))
            # if reader.X> 0:
            #     print('moving')
            #     controller.single_step_trackball(axes[0], 1)
            # else:
            #     controller.single_step_trackball(axes[0], -2)
        if abs(reader.Y) > .1:
            controller.set_single_step_distance(axes[1], reader.Y**3*high_speed)
            controller.single_step(axes[1], 1)
            # if intensity<.95:
            #     controller.set_single_step_distance(axes[1], low_speed)
            # else:
            #     controller.set_single_step_distance(axes[1], high_speed)
            #controller.single_step(axes[1], 1*(2*(reader.Y>0)-1))
            # if reader.Y> 0:
            #     controller.single_step_trackball(axes[1], 1)
            # else:
            #     controller.single_step_trackball(axes[1], -2)

        z = reader.Z - reader.RZ
        if abs(z) > 0.1:
            controller.set_single_step_distance(axes[2],z**3*high_speed)
            controller.single_step(axes[2], 1)
            #z_step = 1 if z > 0 else -2
            # if abs(z)<.95:
            #     controller.set_single_step_distance(axes[2], low_speed)
            # else:
            #     controller.set_single_step_distance(axes[2], high_speed)
            # controller.single_step(axes[2], 1*(2*(z>0)-1))
            #controller.single_step_trackball(axes[2], z_step)

        time.sleep(.05)

    reader.stop()

if __name__ == '__main__':
    dev = LuigsNeumann_SM10()
    run_gamepad2(dev, axes=[7, 8, 9])
