# coding=utf-8
from holypipette.config import Config, NumberWithUnit, Number, Boolean
from holypipette.controller.paramecium import ParameciumController
from holypipette.interface import TaskInterface, command, blocking_command
from holypipette.vision.paramecium_tracking import where_is_paramecium

import numpy as np


class ParameciumConfig(Config):
    downsample = Number(3.37, bounds=(1, 32), doc='Downsampling factor for the image')
    min_gradient = NumberWithUnit(75, bounds=(0, 100), doc='Minimum gradient quantile for edge detection', unit='%')
    max_gradient = NumberWithUnit(98, bounds=(0, 100), doc='Maximum gradient quantile for edge detection', unit='%')
    blur_size = NumberWithUnit(15, bounds=(0, 100), doc='Gaussian blurring size', unit='µm')
    minimum_contour = NumberWithUnit(100, bounds=(0, 1000), doc='Minimum contour length', unit='µm')
    min_length = NumberWithUnit(50, bounds=(0, 1000), doc='Minimum length ellipsis', unit='µm')
    max_length = NumberWithUnit(150, bounds=(0, 1000), doc='Maximum length for ellipsis', unit='µm')
    min_width = NumberWithUnit(5, bounds=(0, 1000), doc='Minimum width for ellipsis', unit='µm')
    max_width = NumberWithUnit(50, bounds=(0, 1000), doc='Maximum width for ellipsis', unit='µm')

    # Vertical distance of pipettes above the coverslip
    working_distance = NumberWithUnit(200, bounds=(0, 1000), doc='Working distance for pipettes', unit='µm')

    categories = [('Tracking', ['downsample','min_gradient', 'max_gradient', 'blur_size', 'minimum_contour',
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

    def __init__(self, pipette_interface, camera):
        super(ParameciumInterface, self).__init__()
        self.config = ParameciumConfig(name='Paramecium')
        self.camera = camera
        self.calibrated_unit = CalibratedUnitProxy(pipette_interface)
        self.controller = ParameciumController(self.calibrated_unit,
                                               pipette_interface.microscope,
                                               pipette_interface.calibrated_stage,
                                               self.config)
        self.paramecium_position = (None, None, None, None, None, None)
        self.tracking = False
        self.follow_paramecium = False

    @blocking_command(category='Paramecium',
                     description='Move pipette down to position at floor level',
                     task_description='Moving pipette to position at floor level')
    def move_pipette_floor(self, xy_position):
        x, y = xy_position
        position = np.array([x, y, self.controller.microscope.floor_Z])
        self.debug('asking for safe move to {}'.format(position))
        self.execute(self.controller.calibrated_unit.safe_move, argument=position)

    @blocking_command(category='Paramecium',
                     description='Move pipette down to position at working distance level',
                     task_description='Moving pipette to position at working distance level')
    def move_pipette_working_level(self, xy_position):
        x, y = xy_position
        position = np.array([x, y, self.controller.microscope.floor_Z + self.config.working_distance*self.controller.microscope.up_direction])
        self.debug('asking for safe move to {}'.format(position))
        self.execute(self.controller.calibrated_unit.safe_move, argument=position)

    @blocking_command(category='Paramecium',
                     description='Move pipette vertically to floor level',
                     task_description='Move pipette vertically to floor level')
    def move_pipette_down(self):
        x, y, _ = self.controller.calibrated_unit.reference_position()
        position = np.array([x, y, self.controller.microscope.floor_Z])
        self.debug('asking for move to {}'.format(position))
        self.execute(self.controller.calibrated_unit.reference_move, argument=position)

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

    @command(category='Paramecium',
             description='Toggle paramecium following')
    def toggle_following(self):
        self.follow_paramecium = not self.follow_paramecium
        if self.follow_paramecium and not self.tracking:
            self.tracking = True

    @command(category='Paramecium',
             description='Display z position of manipulator relative to floor')
    def display_z_manipulator(self):
        position = self.controller.calibrated_unit.reference_position()[2]-self.controller.microscope.floor_Z
        position = position * self.controller.microscope.up_direction # so that >0 means above
        self.info('z position: {} um above floor'.format(position))

    def track_paramecium(self, frame):
        if not self.tracking:
            return
        # Use the size information stored in the camera, in case it exists
        # (only the case for a "camera" that displays a pre-recorded video)
        pixel_per_um = getattr(self.camera, 'pixel_per_um', None)
        if pixel_per_um is None:
            pixel_per_um = self.calibrated_unit.stage.pixel_per_um()[0]
        result = where_is_paramecium(frame, pixel_per_um=pixel_per_um,
                                     previous_x=self.paramecium_position[0],
                                     previous_y=self.paramecium_position[1],
                                     config=self.config)
        self.paramecium_position = result

        if self.follow_paramecium:
            position = np.array(result[:2])
            self.execute(self.controller.calibrated_stage.reference_move, argument=position)

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