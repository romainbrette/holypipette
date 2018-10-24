# coding=utf-8
from holypipette.config import Config, NumberWithUnit, Number, Boolean
from holypipette.controller.paramecium import ParameciumController
from holypipette.interface import TaskInterface, command, blocking_command
from holypipette.vision.paramecium_tracking import where_is_paramecium

import numpy as np


class ParameciumConfig(Config):
    droplet_quantity = Number(1, bounds=(1, 100), doc='Number of microdroplets to make')
    droplet_pressure = NumberWithUnit(15, bounds=(-1000, 1000), doc='Pressure to make droplet', unit='mbar')
    droplet_time = NumberWithUnit(5, bounds=(0, 100), doc='Necessary time to make one droplet', unit='s')

    downsample = Number(3.37, bounds=(1, 32), doc='Downsampling factor for the image')
    min_gradient = NumberWithUnit(50, bounds=(0, 100), doc='Minimum gradient quantile for edge detection', unit='%')
    max_gradient = NumberWithUnit(96, bounds=(0, 100), doc='Maximum gradient quantile for edge detection', unit='%')
    blur_size = NumberWithUnit(10, bounds=(0, 100), doc='Gaussian blurring size', unit='µm')
    minimum_contour = NumberWithUnit(100, bounds=(0, 1000), doc='Minimum contour length', unit='µm')
    min_length = NumberWithUnit(50, bounds=(0, 1000), doc='Minimum length ellipsis', unit='µm')
    max_length = NumberWithUnit(150, bounds=(0, 1000), doc='Maximum length for ellipsis', unit='µm')
    min_width = NumberWithUnit(5, bounds=(0, 1000), doc='Minimum width for ellipsis', unit='µm')
    max_width = NumberWithUnit(50, bounds=(0, 1000), doc='Maximum width for ellipsis', unit='µm')
    categories = [('Droplets', ['droplet_quantity', 'droplet_pressure', 'droplet_time']),
                  ('Tracking', ['downsample','min_gradient', 'max_gradient', 'blur_size', 'minimum_contour',
                                'min_length', 'max_length', 'min_width', 'max_width'])]


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


class ParameciumInterface(TaskInterface):

    def __init__(self, pipette_interface):
        super(ParameciumInterface, self).__init__()
        self.config = ParameciumConfig(name='Paramecium')
        self.calibrated_unit = CalibratedUnitProxy(pipette_interface)
        self.controller = ParameciumController(self.calibrated_unit,
                                               pipette_interface.microscope,
                                               pipette_interface.calibrated_stage,
                                               self.config)
        self.paramecium_position = (None, None, None, None, None, None)
        self.tracking = False

    @blocking_command(category='Paramecium',
                     description='Move pipette down to position at floor level',
                     task_description='Moving pipette to position at floor level')
    def move_pipette_down(self, xy_position):
        x, y = xy_position
        position = np.array([x, y, self.controller.microscope.floor_Z])
        self.debug('asking for safe move to {}'.format(position))
        self.execute(self.controller.calibrated_unit.safe_move, argument=position)

    @command(category='Paramecium',
             description='Start tracking paramecium at mouse position')
    def start_tracking(self, xy_position):
        self.tracking = True
        x, y = xy_position
        self.paramecium_position = (x, y, None, None, None, None)

    @command(category='Paramecium',
             description='Toggle paramecium tracking')
    def toggle_tracking(self):
        self.tracking = not self.tracking

    def track_paramecium(self, frame):
        if not self.tracking:
            return
        result = where_is_paramecium(frame, 1 / self.calibrated_unit.stage.pixel_per_um()[0],
                                     previous_x=self.paramecium_position[0],
                                     previous_y=self.paramecium_position[1],
                                     config=self.config)
        self.paramecium_position = result

    '''
    @command(category='Paramecium',
             description='Store the position of the paramecium tank',
             success_message='Paramecium tank position stored')
    def store_paramecium_position(self):
        self.controller.paramecium_tank_position = self.calibrated_unit.position()

    @blocking_command(category='Paramecium',
                      description='Microdroplet making for paramecium '
                                  'patch clamp',
                      task_description='Microdroplet making')
    def microdroplet_making(self):
        self.execute(self.controller.microdroplet_making)

    @blocking_command(category='Paramecium',
                      description='Calibrated stage moving to compensate the '
                                  'movement of paramecium',
                      task_description='Paramecium tracking')
    def paramecium_movement(self):
        self.execute(self.controller.paramecium_movement)

    @blocking_command(category='Paramecium',
                      description='Moving down the calibrated manipulator to '
                                  'hold the paramecium',
                      task_description='Paramecium immobilization')
    def paramecium_catching(self):
        self.execute(self.controller.paramecium_catching)
    '''