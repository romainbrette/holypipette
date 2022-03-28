'''
Control of manipulators with gamepad

TODO:
- MP Z locking
- Two stage memories, or more
- Command line argument: configuration file

- we might also need fine movements (trackball or steps?)
    fine mvts with left finger? (trackball?)
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

        for i in range(1,10):
            self.dev.set_single_step_velocity(i, 12)

    def load(self, config=None):
        super(GamepadController, self).load(config)
        self.relative_move = self.config["axes"]['relative_move']
        self.direction = self.config["axes"]['direction']
        self.MP_axes = self.config["axes"]['manipulators']
        self.stage_axes = self.config["axes"]['stage']
        self.focus_axis = self.config["axes"]['focus']
        self.how_many_MP = len(self.config['axes']['manipulators'])
        self.dzdx = np.sin(np.pi/180*np.array(self.config.get('angle', [0.] * self.how_many_MP))) # maybe as angle?
        self.memory = self.config.get('memory', None)
        if self.memory is None:
            self.memorize()

    def save(self):
        self.config['angle'] = [float(x) for x in np.arcsin(np.array(self.dzdx))*180/np.pi]
        self.config['memory'] = [float(x) for x in self.memory]
        super(GamepadController, self).save()

    def buffered_relative_move(self, x, axis, fast=False):
        '''
        Issues a relative move only if the axis already doing that movement.
        '''
        if x != self.current_move[axis]:
            if self.current_move[axis] != 0.:
                print('abort')
                self.dev.stop(axis)
            if x!= 0.:
                print('move')
                self.dev.relative_move(x, axis, fast=fast)
            self.current_move[axis] = x

    def quit(self):
        self.terminated = True

    def high_speed_on(self):
        self.high_speed = True

    def high_speed_off(self):
        self.high_speed = False

    def low_speed_on(self):
        self.low_speed = True

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

    def go_to_memorized(self):
        print('Go to')
        self.dev.absolute_move_group(self.memory, self.stage_axes+[self.focus_axis])

    def memorize(self):
        print('Memorize')
        self.memory = self.dev.position_group(self.stage_axes+[self.focus_axis])

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

    def focus(self, Z, direction): # could be a relative move too
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
gamepad = GamepadController(reader, dev, config='~/PycharmProjects/holypipette/development/gamepad.yaml')
gamepad.start()
gamepad.join()
reader.stop()
