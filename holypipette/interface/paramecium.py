# coding=utf-8
from holypipette.config import Config, NumberWithUnit, Number, Boolean
from holypipette.controller.paramecium import ParameciumController
from holypipette.interface import TaskInterface, command, blocking_command
from holypipette.vision.paramecium_tracking import ParameciumTracker
from holypipette.vision import cardinal_points

import numpy as np
import time
from numpy import cos,sin

class ParameciumConfig(Config):
    #downsample = Number(1, bounds=(1, 32), doc='Downsampling factor for the image')
    target_pixelperum = Number(1, bounds=(0, 4), doc='Target number of pixel per um')
    min_gradient = NumberWithUnit(75, bounds=(0, 100), doc='Minimum gradient quantile for edge detection', unit='%')
    max_gradient = NumberWithUnit(98, bounds=(0, 100), doc='Maximum gradient quantile for edge detection', unit='%')
    blur_size = NumberWithUnit(10, bounds=(0, 100), doc='Gaussian blurring size', unit='µm')
    minimum_contour = NumberWithUnit(100, bounds=(0, 1000), doc='Minimum contour length', unit='µm')
    min_length = NumberWithUnit(65, bounds=(0, 1000), doc='Minimum length ellipsis', unit='µm')
    max_length = NumberWithUnit(170, bounds=(0, 1000), doc='Maximum length for ellipsis', unit='µm')
    min_width = NumberWithUnit(30, bounds=(0, 1000), doc='Minimum width for ellipsis', unit='µm')
    max_width = NumberWithUnit(60, bounds=(0, 1000), doc='Maximum width for ellipsis', unit='µm')
    max_displacement = NumberWithUnit(50, bounds=(0, 1000), doc='Maximum displacement over one frame', unit='µm')
    autofocus_size = NumberWithUnit(150, bounds=(0, 1000),
                                    doc='Size of bounding box for autofocus',
                                    unit='µm')
    autofocus_sleep = NumberWithUnit(0.5, bounds=(0, 1),
                                     doc='Sleep time autofocus', unit='s')

    # Automatic experiment
    minimum_stop_time = NumberWithUnit(0, bounds=(0, 5000), doc='Time before starting automation', unit='s')
    stop_duration= NumberWithUnit(50, bounds=(0, 1000), doc='Stopping duration before detection', unit='frames')
    stop_amplitude = NumberWithUnit(5, bounds=(0, 1000), doc='Movement threshold for detecting stop', unit='µm')

    # Vertical distance of pipettes above the coverslip
    working_distance = NumberWithUnit(200, bounds=(0, 1000), doc='Working distance for pipettes', unit='µm')

    # For debugging
    draw_contours = Boolean(False, doc='Draw contours?')
    draw_fitted_ellipses = Boolean(False, doc='Draw fitted ellipses?')

    categories = [('Tracking', ['target_pixelperum','min_gradient', 'max_gradient', 'blur_size', 'minimum_contour',
                                'min_length', 'max_length', 'min_width', 'max_width', 'max_displacement']),
                  ('Manipulation', ['working_distance','autofocus_size','autofocus_sleep']),
                  ('Automation', ['stop_duration', 'stop_amplitude', 'minimum_stop_time']),
                  ('Debugging', ['draw_contours', 'draw_fitted_ellipses'])]


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
        self.calibrated_units = pipette_interface.calibrated_units
        self.controller = ParameciumController(self.calibrated_unit,
                                               pipette_interface.microscope,
                                               pipette_interface.calibrated_stage,
                                               camera,
                                               self.config)
        self.paramecium_position = (None, None, None, None, None, None)
        self.paramecium_info = None
        self.tracking = False
        self.follow_paramecium = False
        self.automate = False
        self.paramecium_tracker = ParameciumTracker(self.config)
        self.previous_shift_click = None
        self.shift_click_time = time.time()-1e6 # a long time ago
        self.timer_t0 = time.time()

    @blocking_command(category='Paramecium',
                     description='Move pipettes to Paramecium',
                     task_description='Moving pipettes to Paramecium')
    def move_pipettes_paramecium(self):
        # Check which pipette is on the right
        orientation = [cardinal_points[self.calibrated_units[i].pipette_position][1] for i in [0,1]]
        if orientation[0] == 2: # east
            right_pipette = 0
            left_pipette = 1
        else: # assuming west
            right_pipette = 1
            left_pipette = 0

        x1, y1 = self.paramecium_position[:2]
        x2, y2 = self.paramecium_tip2_position

        if x1<x2:
            pipette1 = left_pipette
            pipette2 = right_pipette
        else:
            pipette1 = right_pipette
            pipette2 = left_pipette

        # Move pipette 1
        position = np.array([x1, y1, self.controller.microscope.floor_Z])
        self.debug('asking for direct move of pipette 1 to {}'.format(position))
        self.calibrated_units[pipette1].reference_move(position)

        # Move pipette 2
        position = np.array([x2, y2, self.controller.microscope.floor_Z])
        self.debug('asking for direct move of pipette 2 to {}'.format(position))
        self.execute(self.calibrated_units[pipette2].reference_move, argument=position)

        # Clearing history ; the manipulation can be done again
        self.previous_shift_click = None

    @blocking_command(category='Paramecium',
                     description='Move pipettes to position at floor level',
                     task_description='Moving pipettes to position at floor level')
    def move_pipette_floor(self, xy_position):
        t = time.time()
        if t-self.shift_click_time > 5.: # 5 second time-out; could be in config
            self.previous_shift_click = xy_position
            self.shift_click_time = t
            self.debug('Storing position {} for future movement'.format(xy_position))
            self.execute(self.controller.sleep, argument=0.1)
        else:
            # Check which pipette is on the right
            orientation = [cardinal_points[self.calibrated_units[i].pipette_position][1] for i in [0, 1]]
            if orientation[0] == 2:  # east
                right_pipette = 0
                left_pipette = 1
            else:  # assuming west
                right_pipette = 1
                left_pipette = 0

            x1, y1 = self.previous_shift_click
            x2, y2 = xy_position

            if x1 < x2:
                pipette1 = left_pipette
                pipette2 = right_pipette
            else:
                pipette1 = right_pipette
                pipette2 = left_pipette

            # Move pipette 1, except the x axis
            position1 = np.array([x1, y1, self.controller.microscope.floor_Z])
            self.debug('Moving pipette 1 to {}'.format(position1))
            self.calibrated_units[pipette1].reference_move_not_X(position1)

            # Move pipette 2, except the x axis
            position2 = np.array([x2, y2, self.controller.microscope.floor_Z])
            self.debug('Moving pipette 2 to {}'.format(position2))
            self.calibrated_units[pipette2].reference_move_not_X(position2)

            # Wait until motors are stopped
            self.debug('Waiting for pipette 1 to stop')
            self.calibrated_units[pipette1].wait_until_still()
            self.debug('Waiting for pipette 2 to stop')
            self.calibrated_units[pipette2].wait_until_still()

            # Final movements
            self.debug('Moving pipette 1 along X axis')
            self.execute(self.calibrated_units[pipette1].reference_move, argument=position1)
            self.calibrated_units[pipette1].reference_move(position1)
            self.debug('Moving pipette 2 along X axis')
            self.execute(self.calibrated_units[pipette2].reference_move, argument=position2)

            #self.execute(self.calibrated_units[pipette2].reference_move, argument=position)

    @command(category='Paramecium',
                     description='Reset timer')
    def reset_timer(self):
        self.timer_t0 = time.time()

    @command(category='Paramecium',
                     description='Focus on tip')
    def focus(self):
        z = self.calibrated_unit.reference_position()[2]
        self.controller.microscope.absolute_move(z)

    @command(category='Paramecium',
                     description='Perform automatic experiment')
    def automatic_experiment(self):
        self.automate = not self.automate
        if self.automate:
            self.debug('Automatic experiment')
            self.tracking = True
            self.position_list = []  # list of previous positions
        else:
            self.debug('Automatic experiment cancelled')
        self.automate_t0 = time.time()

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

    @blocking_command(category='Paramecium',
                     description='Autofocus',
                     task_description='Autofocus')
    def autofocus(self, xy_position):
        x, y = xy_position
        position = np.array([x, y, self.controller.microscope.position()])
        self.debug('asking for autocus at {}'.format(position))
        self.execute(self.controller.autofocus, argument=position)

    @blocking_command(category='Paramecium',
                     description='Autofocus on Paramecium',
                     task_description='Autofocus on Paramecium')
    def autofocus_paramecium(self):
        if self.tracking:
            x, y = self.paramecium_position[0], self.paramecium_position[1]
            position = np.array([x, y, self.controller.microscope.floor_Z])
            self.debug('asking for autocus at {}'.format(position))
            self.execute(self.controller.autofocus, argument=position)
        else:
            raise StandardError('Paramecium tracking must be switched on first')

    @command(category='Paramecium',
             description='Toggle paramecium tracking')
    def toggle_tracking(self):
        self.tracking = not self.tracking
        if self.tracking:
            self.paramecium_position = (None, None, None, None, None, None)
            self.paramecium_tracker.clear()

    @command(category='Paramecium',
             description='Toggle paramecium following')
    def toggle_following(self):
        self.follow_paramecium = not self.follow_paramecium
        self.debug('Following Paramecium = {}'.format(self.follow_paramecium))
        if self.follow_paramecium and not self.tracking:
            self.tracking = True
            self.paramecium_tracker.clear()

    @command(category='Paramecium',
             description='Display z position of manipulator relative to floor')
    def display_z_manipulator(self):
        position = self.controller.calibrated_unit.reference_position()[2]-self.controller.microscope.floor_Z
        position = position * self.controller.microscope.up_direction # so that >0 means above
        self.info('z position: {} um above floor'.format(position))

    @blocking_command(category='Paramecium',
             description='Detect contact with water',
            task_description='Detect contact with water')
    def detect_contact(self):
        '''
        Detects contact of the pipette with water.
        '''
        self.execute(self.controller.contact_detection)

    def track_paramecium(self, frame):
        if not self.tracking:
            return
        # Use the size information stored in the camera, in case it exists
        # (only the case for a "camera" that displays a pre-recorded video)
        pixel_per_um = getattr(self.camera, 'pixel_per_um', None)
        if pixel_per_um is None:
            pixel_per_um = self.calibrated_unit.stage.pixel_per_um()[0]
        result = self.paramecium_tracker.locate(frame, pixel_per_um=pixel_per_um)
        if result[0] is not None:
            # Center position
            self.paramecium_position = (result.x, result.y, result.MA, result.ma, result.angle)
            # Position of second electrode
            self.paramecium_tip2_position = (result.x+cos(result.angle)*result.MA*.15,
                                             result.y+sin(result.angle)*result.MA*.15)
        self.paramecium_info = result.info

        # Detect if it stops (TODO: analyze angle)
        # TODO: display median shape attributes (or even distribution)
        if self.paramecium_tracker.has_stopped():
            self.info("Paramecium stopped!")
            if self.automate and (self.automate_t0 > time.time() + self.config.minimum_stop_time):
                position = self.paramecium_tracker.median_position()
                self.debug("Impaling")
                self.move_pipettes_paramecium()
                self.automate = False
                self.tracking = False

        # Follow with the stage
        if self.follow_paramecium and result[0] is not None:
            position = np.array(result[:2])
            w,h = self.camera.width, self.camera.height
            move = np.zeros(3)
            move[:2] = .5*(position - np.array([w/2,h/2]))
            self.execute(self.controller.calibrated_stage.reference_relative_move, argument=-move)

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