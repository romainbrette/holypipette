# coding=utf-8
from holypipette.config import Config, NumberWithUnit, Number, Boolean
from holypipette.interface import TaskInterface, command, blocking_command
from holypipette.vision import cardinal_points
from holypipette.controller.paramecium_device import ParameciumDeviceController

import numpy as np
import time

class ParameciumDeviceConfig(Config):
    # Vertical distance of pipettes above the coverslip
    working_level = NumberWithUnit(50, bounds=(0, 500), doc='Working level', unit='µm')
    calibration_level = NumberWithUnit(200, bounds=(0, 1000), doc='Calibration level', unit='µm')
    impalement_level = NumberWithUnit(10, bounds=(0, 100), doc='Impalement level', unit='µm')
    withdraw_distance = NumberWithUnit(1000, bounds=(0, 3000), doc='Withdraw distance', unit='µm')
    pipette_distance = NumberWithUnit(250, bounds=(0, 2000), doc='Pipette distance from center', unit='µm')
    short_withdraw_distance = NumberWithUnit(20, bounds=(0, 100), doc='Withdraw before impalement', unit='µm')

    categories = [('Manipulation', ['working_level', 'calibration_level', 'impalement_level', 'withdraw_distance', 'pipette_distance',
                                    'short_withdraw_distance'])]


class CalibratedUnitProxy(object):
    '''
    Small helper object that forwards all requests to the currently selected
    manipulator.
    '''
    def __init__(self, pipette_interface):
        self._pipette_interface = pipette_interface

    def __getattr__(self, item):
        if item == '_pipette_interface':
            return getattr(super(CalibratedUnitProxy, self), item)

        return getattr(self._pipette_interface.calibrated_unit, item)


class ParameciumDeviceInterface(TaskInterface):

    def __init__(self, pipette_interface, camera):
        super(ParameciumDeviceInterface, self).__init__()
        self.config = ParameciumDeviceConfig(name='Paramecium')
        self.camera = camera
        self.calibrated_unit = CalibratedUnitProxy(pipette_interface)
        self.calibrated_units = pipette_interface.calibrated_units
        self.previous_shift_click = None
        self.shift_click_time = time.time()-1e6 # a long time ago

        self.controller = ParameciumDeviceController(self.calibrated_unit,
                                               pipette_interface.microscope,
                                               pipette_interface.calibrated_stage,
                                               camera,
                                               self.config)

    @command(category='Paramecium',
                     description='Focus on working level')
    def focus_working_level(self):
        self.controller.microscope.absolute_move(self.controller.microscope.floor_Z + self.config.working_level*self.controller.microscope.up_direction)

    @command(category='Paramecium',
                     description='Focus on calibration level')
    def focus_calibration_level(self):
        self.controller.microscope.absolute_move(self.controller.microscope.floor_Z + self.config.calibration_level*self.controller.microscope.up_direction)

    @blocking_command(category='Paramecium',
                     description='Move pipette down to position at working distance level',
                     task_description='Moving pipette to position at working distance level')
    def move_pipette_working_level(self, xy_position):
        x, y = xy_position
        position = np.array([x, y, self.controller.microscope.floor_Z + self.config.working_level*self.controller.microscope.up_direction])
        self.debug('asking for safe move to {}'.format(position))
        self.execute(self.controller.calibrated_unit.safe_move, argument=position)

    @blocking_command(category='Paramecium',
                     description='Move pipette vertically to impalement level',
                     task_description='Moving pipette vertically to impalement level')
    def move_pipette_down(self):
        x, y, _ = self.controller.calibrated_unit.reference_position()
        position = np.array([x, y, self.controller.microscope.floor_Z + self.config.impalement_level*self.controller.microscope.up_direction])
        self.debug('asking for move to {}'.format(position))
        self.execute(self.controller.calibrated_unit.reference_move, argument=position)

    @blocking_command(category='Paramecium',
                      description='Partially withdraw the pipette',
                      task_description='Withdrawing the pipette')
    def move_partial_withdraw(self):
        self.execute(self.controller.calibrated_unit.relative_move, argument=[self.config.withdraw_distance*self.calibrated_unit.up_direction,0])

    @blocking_command(category='Paramecium',
                      description='Move pipette to impalement level by a side move',
                      task_description='Moving pipette to impalement level by a side move')
    def move_pipette_in(self):
        # move out
        self.execute(self.controller.calibrated_unit.relative_move, argument=[self.config.short_withdraw_distance*self.calibrated_unit.up_direction[0],0])
        # move down
        x, y, _ = self.controller.calibrated_unit.reference_position()
        position = np.array([x, y, self.controller.microscope.floor_Z + self.config.impalement_level*self.controller.microscope.up_direction])
        self.execute(self.controller.calibrated_unit.reference_move, argument=position)
        # move in
        self.execute(self.controller.calibrated_unit.relative_move, argument=[-self.config.short_withdraw_distance*self.calibrated_unit.up_direction,0])

    #@blocking_command(category='Paramecium',
    #                  description='Partially withdraw the pipette',
    #                  task_description='Withdrawing the pipette')
    #def set_center(self):
        #self.center = self.cali

        #self.register_key_action(Qt.Key_At, None,
        #                         self.paramecium_interface.set_center)
        #self.register_key_action(Qt.Key_Home, None,
        #                         self.paramecium_interface.move_to_center)
