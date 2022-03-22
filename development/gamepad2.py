'''
Control of manipulators with gamepad

TODO: axes configuration (maybe from file), step distances
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

    def go_to_memorized(self):
        print('Go to')
        self.dev.absolute_move_group(self.memory, self.stage_axes)

    def memorize(self):
        print('Memorize')
        self.memory = self.dev.position_group(self.stage_axes)

    def withdraw(self, direction):
        print('Withdraw')
        direction = int(direction)

    def stop_move_in(self):
        print('Stop move in')

    def MP_virtualX_Y(self, X, Y, directionX, directionY):
        X = X*int(directionX)*self.step_distance
        Y = Y * int(directionY)*self.step_distance
        print('MP',X,Y)

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

dev = LuigsNeumann_SM10()
reader = GamepadReader()
reader.start()
gamepad = GamepadController(reader, dev, config='~/PycharmProjects/holypipette/development/gamepad.yaml')
gamepad.start()
gamepad.stop()
reader.stop()
