'''
Control of manipulators with gamepad

TODO:
- axes configuration (maybe from file), step distances
- method parameters should be stored rather than passed as parameters
'''
from holypipette.devices.gamepad import *
import os
import time
from holypipette.devices.manipulator.luigsneumann_SM10 import LuigsNeumann_SM10

how_many_MP = 2

class GamepadController(GamepadProcessor):
    def __init__(self, gamepad_reader, dev, config=None):
        super(GamepadController, self).__init__(gamepad_reader, config=config)
        self.current_MP = 0
        self.locked = [False]*how_many_MP
        self.all_locked = False
        self.dev = dev
        self.MP_axes = [[1,2,3], [4,5,6]]
        self.stage_axes = [7,8]
        self.focus_axis = 9
        self.step_distance = 10. # should be in configuration file
        self.memory = None # should be in configuration file
        self.calibration_position = [None]*how_many_MP
        self.dzdx = [0.]*how_many_MP # movement in z for a unit movement in x

    def quit(self):
        self.terminated = True

    def select_manipulator(self):
        self.current_MP = (self.current_MP + 1) % how_many_MP
        print('Selected manipulator:', self.current_MP+1)

    def lock_MP(self):
        self.locked[self.current_MP] = not self.locked[self.current_MP]

    def lock_all_MP(self):
        if all(self.locked):
            self.locked = [False]*how_many_MP
        else:
            self.locked = [True] * how_many_MP

    def calibrate(self):
        print('Calibrate')
        position = self.dev.position_group(self.MP_axes[self.current_MP])
        if self.calibration_position[self.current_MP] is not None:
            dx, dz = position[0] - self.calibration_position[self.current_MP][0], position[2] - self.calibration_position[self.current_MP][2]
            self.dzdx[self.current_MP] = dz/dx
            print(dz/dx)
        self.calibration_position[self.current_MP] = position

    def go_to_memorized(self):
        print('Go to')
        self.dev.absolute_move_group(self.memory, self.stage_axes)

    def memorize(self):
        print('Memorize')
        self.memory = self.dev.position_group(self.stage_axes)

    def withdraw(self, direction):
        print('Withdraw')
        direction = int(direction)
        self.dev.set_home_direction(self.MP_axes[self.current_MP], direction)
        self.dev.home(self.MP_axes[self.current_MP])

    def stop_move_in(self):
        print('Stop move in')
        self.dev.home_abort(self.MP_axes[self.current_MP])

    def MP_virtualX_Y(self, X, Y, directionX, directionY):
        X = X*int(directionX)*self.step_distance
        Y = Y * int(directionY)*self.step_distance
        print('MP',X,Y)
        dzdx = self.dzdx[self.current_MP]
        X = X/(1+dzdx**2)**.5
        Z = X*dzdx/(1+dzdx**2)**.5
        for i, d in enumerate([X,Y,Z]):
            self.dev.set_single_step_distance(self.stage_axes[self.current_MP][i], d)
            self.dev.single_step(self.stage_axes[self.current_MP][i], 1)

    def stage_XY(self, X, Y, directionX, directionY):
        X = X*int(directionX)*self.step_distance
        Y = Y * int(directionY)*self.step_distance
        print('Stage',X,Y)
        for i, d in enumerate([X,Y]):
            self.dev.set_single_step_distance(self.stage_axes[i], d)
            self.dev.single_step(self.stage_axes[i], 1)

    def MP_fineXY(self, X, Y, directionX, directionY):
        X = X*int(directionX)*self.step_distance
        Y = Y * int(directionY)*self.step_distance
        print('MP fine',X,Y)
        for i, d in enumerate([X,Y]):
            self.dev.set_single_step_distance(self.stage_axes[self.current_MP][i], d)
            self.dev.single_step(self.stage_axes[self.current_MP][i], 1)

    def focus(self, Z, direction):
        Z = Z*int(direction)*self.step_distance
        print('Focus',Z)
        self.dev.set_single_step_distance(self.focus_axis, Z)
        self.dev.single_step(self.focus_axis, 1)

    def MP_Z(self, direction):
        d = int(direction)*self.step_distance
        self.dev.set_single_step_distance(self.stage_axes[self.current_MP][2], d)
        self.dev.single_step(self.stage_axes[self.current_MP][2], 1)
        if self.locked[self.current_MP]:
            self.focus(1., direction) # might not be the right direction!
            # if others are locked, move them too
            if all(self.locked):
                current_MP = self.current_MP
                for i in range(len(self.locked)):
                    if i!= current_MP:
                        self.current_MP = i
                        self.MP_Z(direction) # might not be the right direction!
                self.current_MP = current_MP


dev = LuigsNeumann_SM10()
reader = GamepadReader()
reader.start()
gamepad = GamepadController(reader, dev, config='~/PycharmProjects/holypipette/development/gamepad.yaml')
gamepad.start()
gamepad.stop()
reader.stop()
