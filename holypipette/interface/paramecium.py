# coding=utf-8
from holypipette.config import Config, NumberWithUnit, Number, Boolean
from holypipette.controller.paramecium import ParameciumController
from holypipette.interface import TaskInterface, command, blocking_command
from holypipette.vision.paramecium_tracking import ParameciumTracker
from holypipette.vision import cardinal_points

import nidaqmx
task = nidaqmx.Task()
task.ai_channels.add_ai_voltage_chan("Dev1/ai0")

import cv2
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
    working_distance = NumberWithUnit(50, bounds=(0, 1000), doc='Working distance for pipettes', unit='µm')

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
        self.found = False
        self.binary_image = []
        #self.fgbg = cv2.bgsegm.createBackgroundSubtractorMOG()
        self.fgbg = cv2.createBackgroundSubtractorKNN()

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
            self.calibrated_units[pipette1].reference_move_not_Z(position1)

            # Move pipette 2, except the x axis
            position2 = np.array([x2, y2, self.controller.microscope.floor_Z])
            self.debug('Moving pipette 2 to {}'.format(position2))
            self.calibrated_units[pipette2].reference_move_not_Z(position2)

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
        from holypipette.gui import movingList
        if not movingList.detect_paramecium:
            return
        pixel_per_um = self.calibrated_unit.stage.pixel_per_um()[0]
        kernel1 = np.ones((2, 2), np.uint8)
        kernel2 = np.ones((5, 5), np.uint8)
        kernel3 = np.ones((11, 11), np.uint8)
        if self.found == False:
            gray1 = self.fgbg.apply(frame)
        else:
            gray1 = self.fgbg.apply(frame, learningRate=0)
        #gray1 = cv2.medianBlur(gray1,5)
        gray1 = cv2.GaussianBlur(gray1, (7, 7), 0)
        ret, otsu = cv2.threshold(gray1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        opening = cv2.morphologyEx(otsu, cv2.MORPH_OPEN, kernel1)
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel1)
        dilation = cv2.dilate(closing, kernel2, iterations=10)
        erosion = cv2.erode(dilation, kernel2, iterations=10)
        final_closing = cv2.morphologyEx(erosion, cv2.MORPH_CLOSE, kernel3)

        still_time = 1

        self.binary_image.append(final_closing)
        if (len(self.binary_image) > still_time*30):
            compare_matrix = self.binary_image[-still_time*30:]
            bit_and = self.binary_image[-still_time*30]
            for c in range(1-still_time*30, -1):
                bit_and = cv2.bitwise_and(bit_and, compare_matrix[c])
            cv2.imshow("TESTING", bit_and)
            contours, hierarchy = cv2.findContours(bit_and, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                if (cv2.arcLength(cnt, True) > self.config.minimum_contour * pixel_per_um) and(len(cnt) >= 5):
                    (x, y), (ma, MA), theta = cv2.fitEllipse(np.squeeze(cnt))
                    MA, ma = MA / pixel_per_um, ma / pixel_per_um
                    if (MA > self.config.max_length or ma > self.config.max_width):
                        self.found = False
                        break
                    if (MA > self.config.min_length and ma > self.config.min_width and MA < self.config.max_length and ma < self.config.max_width):
                        M = cv2.moments(cnt)
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])
                        cv2.circle(frame, (cX, cY), 5, (255, 255, 255), -1)
                        movingList.detect_paramecium = False
                        movingList.paramecium_position = cX, cY
                        cv2.imwrite('C:/Users/inters/Desktop/test1/test.jpg', frame)
                        print("HOANG TEST DONE")

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