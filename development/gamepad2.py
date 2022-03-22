'''
Control of manipulators with gamepad

TODO:
- method parameters should be stored rather than passed as parameters
- Check the status of the axis before movement?
- Z clicks should be continuous
- velocity should probably be adjusted to distance
- maybe a trackball mode and a fine mode depending on intensity
- cross : with acceleration / switch to trackball
- alternative is to use relative moves that get aborted (eg for cross)

cross and Z clicks: as events, relative_move with abortion

>> Switching with duration:
- If in the same state for a long time, then switch to fast mode.
- When in fast mode, return to slow mode when no movement at all (maybe for some time).
- When switching to fast mode, a large relative movement is triggered (in the right direction).
- As soon as movement changes, movement is aborted then a new movement is triggered.
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
        #self.memory = None # should be in configuration file
        self.calibration_position = [None]*how_many_MP
        #self.dzdx = [0.]*how_many_MP # movement in z for a unit movement in x
        self.withdrawn = False

        #for i in range(1,10):
        #    self.dev.set_single_step_velocity(i, 12)

    def load(self, config=None):
        super(GamepadController, self).load(config)
        self.MP_axes = self.config["axes"]['manipulators']
        self.stage_axes = self.config["axes"]['stage']
        self.focus_axis = self.config["axes"]['focus']
        self.dzdx = self.config.get('dzdx', [0.]*how_many_MP) # maybe as angle?
        self.memory = self.config.get('memory', None)
        if self.memory is None:
            self.memorize()

    def save(self):
        self.config['dzdx'] = self.dzdx
        self.config['memory'] = self.memory
        super(GamepadController, self).save()

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

    def stop_withdraw(self):
        print('Aborting')
        self.dev.stop(self.MP_axes[self.current_MP][0])

    def MP_virtualX_Y(self, X, Y, directionX, directionY, high_speed=False):
        X = X*float(directionX)
        Y = Y * float(directionY)
        #print('MP',X,Y)
        dzdx = self.dzdx[self.current_MP]
        X = X/(1+dzdx**2)**.5
        Z = X*dzdx/(1+dzdx**2)**.5
        for i, d in enumerate([X,Y,Z]):
            self.dev.set_single_step_distance(self.MP_axes[self.current_MP][i], d)
            self.dev.single_step(self.MP_axes[self.current_MP][i], 1)

    def stage_XY(self, X, Y, directionX, directionY, high_speed=False):
        X = X*float(directionX)
        Y = Y * float(directionY)
        #print('Stage',X,Y)
        for i, d in enumerate([X,Y]):
            self.dev.set_single_step_distance(self.stage_axes[i], d)
            self.dev.single_step(self.stage_axes[i], 1)

    def MP_fine_XZ(self, X, Z, directionX, directionZ, high_speed=False):
        X = X*float(directionX)
        Z = Z * float(directionZ)
        #print('MP fine',X,Z)
        for i, d in enumerate([(0,X), (2,Z)]):
            self.dev.set_single_step_distance(self.MP_axes[self.current_MP][i], d)
            self.dev.single_step(self.MP_axes[self.current_MP][i], 1)
        # Locked movements
        if self.locked[self.current_MP]:
            dzdx = self.dzdx[self.current_MP]
            self.focus(1., Z + X*dzdx) # or the opposite?
            # if others are locked, move them too
            if all(self.locked):
                current_MP = self.current_MP
                for i in range(len(self.locked)):
                    if i!= current_MP:
                        self.current_MP = i
                        self.MP_Z(Z) # might not be the right direction!
                self.current_MP = current_MP

    def focus(self, Z, direction, high_speed=False):
        Z = Z*float(direction)
        print('Focus',Z)
        self.dev.set_single_step_distance(self.focus_axis, Z)
        self.dev.single_step(self.focus_axis, 1)

    def MP_Z(self, direction, high_speed=False):
        d = float(direction)
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
