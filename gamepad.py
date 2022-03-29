'''
Control of manipulators with gamepad

TODO:
- Sometimes the manipulator doesn't stop moving, why? (print current_move)
    not sure abort_all works
    maybe we should instead check the status of the axis
            ret = struct.unpack('20B', self.send_command('A120', data, 20))
            moving = [ret[6 + i * 4] for i in range(len(axes))]
            is_moving = any(moving)
    maybe check status after stopping?
- Fine movements (trackball or steps?)
- Command line argument: configuration file
- note : placement of MP every 15 deg
'''
from holypipette.devices.gamepad import *
import os
import time
from holypipette.devices.manipulator.luigsneumann_SM10 import LuigsNeumann_SM10
import numpy as np

class GamepadController(GamepadProcessor):
    def __init__(self, gamepad_reader, dev, config=None):
        self.dev = dev
        super(GamepadController, self).__init__(gamepad_reader, config=config)
        self.current_MP = 0
        self.calibration_position = [None]*self.how_many_MP
        self.high_speed = False
        self.low_speed = False
        self.XY_on = False
        self.XZ_on = False
        self.locked = False

        ## Axes moves
        self.current_move = [0.]*100 # That's many possible axes

        #for i in range(1,10):
        #    self.dev.set_single_step_velocity(i, 12)

    def load(self, config=None):
        super(GamepadController, self).load(config)
        self.relative_move = self.config['relative_move']
        self.direction = self.config["axes"]['direction']
        self.MP_axes = self.config["axes"]['manipulators']
        self.stage_axes = self.config["axes"]['stage']
        self.focus_axis = self.config["axes"]['focus']
        self.how_many_MP = len(self.config['axes']['manipulators'])
        self.dzdx = np.sin(np.pi/180*np.array(self.config.get('angle', [0.] * self.how_many_MP))) # maybe as angle?
        self.memory_init = self.config.get('memory_init', None)
        self.working_level = self.config.get('working_level', None)

    def save(self):
        self.config['angle'] = [float(x) for x in np.arcsin(np.array(self.dzdx))*180/np.pi]
        self.config['memory_init'] = [float(x) for x in self.memory_init]
        self.config['working_level'] = [float(x) for x in self.working_level]
        super(GamepadController, self).save()

    def init_axes(self):
        '''
        Move all axes home and reset positions.
        '''
        # Move home
        for MP_axes in self.MP_axes:
            for axis in MP_axes:
                self.dev.home(axis)
        for axis in self.stage_axes:
            self.dev.home(axis)
        self.dev.home(self.focus_axis)

        # Wait untill still
        for MP_axes in self.MP_axes:
            self.dev.wait_until_still(MP_axes)
        self.dev.wait_until_still(self.stage_axes+[self.focus_axis])

        # Zero
        for MP_axes in self.MP_axes:
            for axis in MP_axes:
                self.dev.zero(axis)
        for axis in self.stage_axes:
            self.dev.zero(axis)
        self.dev.zero(self.focus_axis)

    def buffered_relative_move(self, x, axis, fast=False):
        '''
        Issues a relative move only if the axis is not already doing that movement.
        '''
        if x != self.current_move[axis]:
            if self.current_move[axis] != 0.:
                self.dev.stop(axis)
            if x!= 0.:
                self.dev.relative_move(x, axis, fast=fast)
            self.current_move[axis] = x

    def quit(self):
        self.terminated = True

    def abort_all(self, force=True):
        for axis in range(1, len(self.direction)):
            if force or (self.current_move[axis] != 0.):
                self.dev.stop(axis)
                self.current_move[axis] = 0.

    def lock(self):
        self.locked = not self.locked
        if self.locked:
            print('Locked')
        else:
            print('Unlocked')

    def high_speed_on(self):
        self.high_speed = True
        self.abort_all()

    def high_speed_off(self):
        self.high_speed = False
        self.abort_all()

    def low_speed_on(self):
        self.low_speed = True
        self.abort_all()

    def low_speed_off(self):
        self.low_speed = False

    def select_manipulator(self):
        self.current_MP = (self.current_MP + 1) % self.how_many_MP
        print('Selected manipulator:', self.current_MP+1)

    def calibrate(self):
        print('Calibrate')
        position = self.dev.position_group(self.MP_axes[self.current_MP])
        if self.calibration_position[self.current_MP] is not None:
            dx, dz = position[0] - self.calibration_position[self.current_MP][0], position[2] - self.calibration_position[self.current_MP][2]
            if dx != 0:
                self.dzdx[self.current_MP] = dz/dx
                print(dz/dx)
        self.calibration_position[self.current_MP] = position

    def go_to_init(self):
        print('Go to init position')
        # Focus first
        self.dev.absolute_move(self.memory_init[2], self.focus_axis)
        # Then the rest
        self.dev.absolute_move_group(self.memory_init[:2], self.stage_axes)
        for i, MP_axes in enumerate(self.MP_axes):
            self.dev.absolute_move_group(self.memory_init[3+3*i:6+3*i], MP_axes)

    def memorize_init(self):
        # Init position
        print('Memorize init position')
        self.memory_init = [self.dev.position_group(self.stage_axes+[self.focus_axis])] +\
                           [self.dev.position_group(MP_axes for MP_axes in self.MP_axes)]

    def memorize_working_level(self):
        print('Memorize working level')
        self.working_level = self.dev.position(self.focus_axis)

    def go_to_working_level(self):
        # Move focus and manipulators to working level
        # First calculate the relative move
        dz = self.working_level - self.dev.position(self.focus_axis)
        # Move manipulators, then focus
        for i, MP_axes in enumerate(self.MP_axes):
            self.dev.relative_move_group(dz, MP_axes[2])
        self.dev.relative_move_group(dz, self.focus_axis[2])

    # def MP_virtualX_Y(self, X, Y, directionX, directionY):
    #     X = X*float(directionX)
    #     Y = Y * float(directionY)
    #     if (X!=0.) or (Y!=0.):
    #         #print('MP',X,Y)
    #         dzdx = self.dzdx[self.current_MP]
    #         X = X/(1+dzdx**2)**.5
    #         Z = X*dzdx/(1+dzdx**2)**.5
    #         for i, d in enumerate([X,Y,Z]):
    #             self.dev.set_single_step_distance(self.MP_axes[self.current_MP][i], d)
    #             self.dev.single_step(self.MP_axes[self.current_MP][i], 1)

    def stage_XY(self, X, Y):
        X, Y = self.discrete_state8(X, Y)
        X = X*self.relative_move*self.direction[self.stage_axes[0]]
        Y = Y*self.relative_move*self.direction[self.stage_axes[1]]

        self.buffered_relative_move(X, self.stage_axes[0], fast=self.high_speed)
        self.buffered_relative_move(Y, self.stage_axes[1], fast=self.high_speed)

    def MP_XZ(self, X, Z):
        X, Z = self.discrete_state8(X, Z)
        X = X*self.relative_move*self.direction[self.MP_axes[self.current_MP][0]]
        Z = Z*self.relative_move*self.direction[self.MP_axes[self.current_MP][2]]

        if not self.XY_on:
            self.buffered_relative_move(X, self.MP_axes[self.current_MP][0], fast=self.high_speed)
            self.XZ_on = (X != 0.)
        self.buffered_relative_move(Z, self.MP_axes[self.current_MP][2], fast=self.high_speed)
        if self.locked:
            for i, axes in enumerate(self.MP_axes):
                if i != self.current_MP:
                    self.buffered_relative_move(Z, axes[2], fast=self.high_speed)
        self.previous_MP_X = X

    def MP_XY(self, X, Y):
        X, Y = self.discrete_state8(X, Y)
        X = X*self.relative_move*self.direction[self.MP_axes[self.current_MP][0]]
        Y = Y*self.relative_move*self.direction[self.MP_axes[self.current_MP][1]]

        self.XY_on = (X != 0.)
        if not self.XZ_on:
            self.buffered_relative_move(X, self.MP_axes[self.current_MP][0], fast=self.high_speed)
        self.buffered_relative_move(Y, self.MP_axes[self.current_MP][1], fast=self.high_speed)
        self.previous_MP_X = X

    def focus(self, Z): # could be a relative move too
        Z = np.sign(Z)*self.relative_move*self.direction[self.focus_axis]
        self.buffered_relative_move(Z, self.focus_axis, fast=self.high_speed)

    def focus_step(self, Z, direction): # could be a relative move too
        Z = Z*float(direction)
        if Z!=0.:
            self.dev.set_single_step_distance(self.focus_axis, Z)
            self.dev.single_step(self.focus_axis, 1)

    # def MP_Z_step(self, direction):
    #     d = float(direction)
    #     self.dev.set_single_step_distance(self.MP_axes[self.current_MP][2], d)
    #     self.dev.single_step(self.MP_axes[self.current_MP][2], 1)


dev = LuigsNeumann_SM10(stepmoves=False)
reader = GamepadReader()
reader.start()
gamepad = GamepadController(reader, dev, config='~/PycharmProjects/holypipette/gamepad.yaml')
gamepad.start()
gamepad.join()
reader.stop()
