'''
Control of manipulators with gamepad

TODO:
- high speed is not very speedy!
- relative moves cannot be planar! so planar movements can only be fine
- relative moves must be discretized!! (constant speed along each axis)
=> each axis must be have an ongoing state, no need to check position
- axis signs should be stored rather than passed as parameters?
- Command line argument: configuration file
- Switching with finger buttons, and remove cross configuration
    high_speed : fast relative move
    low_speed : small steps
    neither : slow relative move
    -> for joysticks/cross, check if state changed (if so, abort)

=> all hardware axes may move with relative moves
=> virtual axes can only move with steps
unless we use rps (will be approximate) or fix by measurement
XZ : relative moves on cross
virtual X, Y: steps only (but how about Y?)

Note: relative move takes time to stop in fast mode.
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
        self.locked = [False]*self.how_many_MP
        self.all_locked = False
        #self.memory = None # should be in configuration file
        self.calibration_position = [None]*self.how_many_MP
        #self.dzdx = [0.]*how_many_MP # movement in z for a unit movement in x
        self.withdrawn = False
        self.high_speed = False
        self.low_speed = False

        for i in range(1,10):
            self.dev.set_single_step_velocity(i, 12)

    def load(self, config=None):
        super(GamepadController, self).load(config)
        self.MP_axes = self.config["axes"]['manipulators']
        self.stage_axes = self.config["axes"]['stage']
        self.focus_axis = self.config["axes"]['focus']
        self.how_many_MP = len(self.config['axes']['manipulators'])
        #self.dzdx = self.config.get('dzdx', [0.]*self.how_many_MP) # maybe as angle?
        self.dzdx = np.sin(np.pi/180*np.array(self.config.get('angle', [0.] * self.how_many_MP))) # maybe as angle?
        self.memory = self.config.get('memory', None)
        if self.memory is None:
            self.memorize()
        self.stage_ongoing = (0., 0.) # Ongoing relative movement

    def save(self):
        #self.config['dzdx'] = self.dzdx
        self.config['angle'] = [float(x) for x in np.arcsin(np.array(self.dzdx))*180/np.pi]
        self.config['memory'] = [float(x) for x in self.memory]
        super(GamepadController, self).save()

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

    def lock_MP(self):
        self.locked[self.current_MP] = not self.locked[self.current_MP]
        print('Manipulator', self.current_MP, 'lock:', self.locked[self.current_MP])

    def lock_all_MP(self):
        if all(self.locked):
            self.locked = [False]*self.how_many_MP
            print('Manipulator unlocked')
        else:
            self.locked = [True] * self.how_many_MP
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

    def MP_virtualX_Y(self, X, Y, directionX, directionY):
        X = X*float(directionX)
        Y = Y * float(directionY)
        if (X!=0.) or (Y!=0.):
            print('MP',X,Y)
            dzdx = self.dzdx[self.current_MP]
            X = X/(1+dzdx**2)**.5
            Z = X*dzdx/(1+dzdx**2)**.5
            for i, d in enumerate([X,Y,Z]):
                self.dev.set_single_step_distance(self.MP_axes[self.current_MP][i], d)
                self.dev.single_step(self.MP_axes[self.current_MP][i], 1)

    def stage_XY(self, X, Y, directionX, directionY):
        X = X*float(directionX)
        Y = Y * float(directionY)
        if not self.low_speed:
            if self.stage_ongoing != (X, Y):
                if self.stage_ongoing != (0., 0.):
                    self.dev.stop(self.stage_axes[0])
                    self.dev.stop(self.stage_axes[1])
                    print('Stage abort')
                if (X!=0.) or (Y!=0.):
                    print('Stage speed move',X,Y,', high speed = ',self.high_speed)
                    self.dev.relative_move(5000.*np.sign(X), self.stage_axes[0], fast=self.high_speed)
                    self.dev.relative_move(5000.*np.sign(Y), self.stage_axes[1], fast=self.high_speed)
                self.stage_ongoing = (X, Y)
        else: # steps
            if self.stage_ongoing != (0., 0.):
                self.dev.stop(self.stage_axes[0])
                self.dev.stop(self.stage_axes[1])
                print('Stage abort')
                self.stage_ongoing = (0., 0.)
            for i, d in enumerate([X,Y]):
                self.dev.set_single_step_distance(self.stage_axes[i], d)
                self.dev.single_step(self.stage_axes[i], 1)

    def MP_fine_XZ(self, X, Z, directionX, directionZ):
        X = X*float(directionX)
        Z = Z * float(directionZ)
        if (X!=0.) or (Z!=0.):
            print('MP fine',X,Z)
            for i, d in [(0,X), (2,Z)]:
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
                            self.MP_Z_step(Z) # might not be the right direction!
                    self.current_MP = current_MP

    def focus(self, Z, direction):
        Z = Z*float(direction)
        if Z!=0.:
            print('Focus',Z)
            self.dev.set_single_step_distance(self.focus_axis, Z)
            self.dev.single_step(self.focus_axis, 1)

    # def MP_Z(self, direction):
    #     d = float(direction)
    #     print('MP Z', d)
    #     if d == 0.: # abort
    #         print("aborting")
    #         self.dev.stop(self.MP_axes[self.current_MP][2])
    #     else:
    #         print('relative move', d)
    #         self.dev.relative_move(d, self.MP_axes[self.current_MP][2], fast=False)

    def MP_Z_step(self, direction):
        d = float(direction)
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
                        self.MP_Z_step(direction) # might not be the right direction!
                self.current_MP = current_MP


dev = LuigsNeumann_SM10(stepmoves=False)
reader = GamepadReader()
reader.start()
gamepad = GamepadController(reader, dev, config='~/PycharmProjects/holypipette/development/gamepad.yaml')
gamepad.start()
gamepad.join()
reader.stop()
