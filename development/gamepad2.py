'''
Control of manipulators with gamepad

TODO:
- axes configuration (maybe from file), step distances
- method parameters should be stored rather than passed as parameters

- Check the status of the axis before movement?
- Maybe abort movement when joystick is 0
- Z clicks should be continuous
- velocity should probably be adjusted to distance
- MP movements are a bit too fine
- maybe a trackball mode and a fine mode depending on intensity
- save dxdz to file
- cross : with acceleration / switch to trackball
- locked fine XZ
- alternative is to use relative moves that get aborted (eg for cross)
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
        self.step_distance = 1. # should be in configuration file
        self.memory = None # should be in configuration file
        self.calibration_position = [None]*how_many_MP
        self.dzdx = [0.]*how_many_MP # movement in z for a unit movement in x
        self.withdrawn = False

        for i in range(1,10):
            self.dev.set_single_step_velocity(i, 12)

    def quit(self):
        self.terminated = True

    def select_manipulator(self):
        self.current_MP = (self.current_MP + 1) % how_many_MP
        print('Selected manipulator:', self.current_MP+1)

    def lock_MP(self):
        self.locked[self.current_MP] = not self.locked[self.current_MP]
        print('Manipulator', self.current_MP, 'lock:', self.locked[self.current_MP])

    def lock_all_MP(self):
        if all(self.locked):
            self.locked = [False]*how_many_MP
            print('Manipulator unlocked')
        else:
            self.locked = [True] * how_many_MP
            print('Manipulator locked')

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

    def withdraw(self, direction):
        print('Withdraw')
        direction = float(direction)
        if self.withdrawn:
            self.withdrawn = False
            self.dev.relative_move(-direction, self.MP_axes[self.current_MP][0], fast=True)
        else:
            self.withdrawn = True
            self.dev.relative_move(direction, self.MP_axes[self.current_MP][0], fast=True)
        print('done')

    def stop_move_in(self):
        print('Aborting')
        self.dev.stop(self.MP_axes[self.current_MP][0])

    def MP_virtualX_Y(self, X, Y, directionX, directionY):
        X = X*float(directionX)*self.step_distance
        Y = Y * float(directionY)*self.step_distance
        print('MP',X,Y)
        dzdx = self.dzdx[self.current_MP]
        X = X/(1+dzdx**2)**.5
        Z = X*dzdx/(1+dzdx**2)**.5
        for i, d in enumerate([X,Y,Z]):
            self.dev.set_single_step_distance(self.MP_axes[self.current_MP][i], d)
            self.dev.single_step(self.MP_axes[self.current_MP][i], 1)

    def stage_XY(self, X, Y, directionX, directionY):
        X = X*float(directionX)*self.step_distance
        Y = Y * float(directionY)*self.step_distance
        print('Stage',X,Y)
        for i, d in enumerate([X,Y]):
            self.dev.set_single_step_distance(self.stage_axes[i], d)
            self.dev.single_step(self.stage_axes[i], 1)

    def MP_fine_XZ(self, X, Z, directionX, directionZ):
        X = X*float(directionX)*self.step_distance
        Z = Z * float(directionZ)
        print('MP fine',X,Z)
        self.dev.set_single_step_distance(self.MP_axes[self.current_MP][0], X)
        self.dev.single_step(self.MP_axes[self.current_MP][0], 1)
        self.MP_Z(Z)

    def focus(self, Z, direction):
        Z = Z*float(direction)*self.step_distance
        print('Focus',Z)
        self.dev.set_single_step_distance(self.focus_axis, Z)
        self.dev.single_step(self.focus_axis, 1)

    def MP_Z(self, direction):
        d = float(direction)*self.step_distance
        print('MP Z', d)
        self.dev.set_single_step_distance(self.MP_axes[self.current_MP][2], d)
        self.dev.single_step(self.MP_axes[self.current_MP][2], 1)
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


dev = LuigsNeumann_SM10(stepmoves=False)
reader = GamepadReader()
reader.start()
gamepad = GamepadController(reader, dev, config='~/PycharmProjects/holypipette/development/gamepad.yaml')
gamepad.start()
gamepad.join()
reader.stop()
