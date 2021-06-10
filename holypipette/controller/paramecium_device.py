from .base import TaskController
from time import sleep
from scipy.optimize import golden, minimize_scalar
from numpy import array,arange
import numpy as np

class ParameciumDeviceController(TaskController):
    def __init__(self, calibrated_unit, microscope,
                 calibrated_stage, camera, config):
        super(ParameciumDeviceController, self).__init__()
        self.config = config
        self.calibrated_unit = calibrated_unit
        self.calibrated_stage = calibrated_stage
        self.microscope = microscope
        self.camera = camera

    def partial_withdraw(self):
        self.calibrated_unit.relative_move(self.config.withdraw_distance * self.calibrated_unit.up_direction[0], 0)

    def move_pipette_in(self):
        '''
        It is assumed that the pipette is at working level.
        '''
        # move out
        self.calibrated_unit.relative_move(self.config.short_withdraw_distance*self.calibrated_unit.up_direction[0],0)
        self.calibrated_unit.wait_until_still()
        # move down
        movement = np.array([0, 0, -(self.config.working_level-self.config.impalement_level)*self.microscope.up_direction])
        self.calibrated_unit.reference_relative_move(movement)
        self.calibrated_unit.wait_until_still()
        # move in
        self.calibrated_unit.relative_move(-self.config.short_withdraw_distance*self.calibrated_unit.up_direction[0],0)
