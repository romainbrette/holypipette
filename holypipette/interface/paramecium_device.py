# coding=utf-8
from holypipette.config import Config, NumberWithUnit, Number, Boolean
from holypipette.interface import TaskInterface, command, blocking_command
from holypipette.vision import cardinal_points

import numpy as np
import time

class ParameciumDeviceConfig(Config):
    # Vertical distance of pipettes above the coverslip
    working_distance = NumberWithUnit(200, bounds=(0, 1000), doc='Working distance for pipettes', unit='µm')

    categories = [('Manipulation', ['working_distance'])]


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
                     description='Focus on tip')
    def focus(self):
        z = self.calibrated_unit.reference_position()[2]
        self.controller.microscope.absolute_move(z)

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

    @blocking_command(category='Paramecium',
                     description='Autofocus',
                     task_description='Autofocus')
    def autofocus(self, xy_position):
        x, y = xy_position
        position = np.array([x, y, self.controller.microscope.position()])
        self.debug('asking for autocus at {}'.format(position))
        self.execute(self.controller.autofocus, argument=position)

    @command(category='Paramecium',
             description='Display z position of manipulator relative to floor')
    def display_z_manipulator(self):
        position = self.controller.calibrated_unit.reference_position()[2]-self.controller.microscope.floor_Z
        position = position * self.controller.microscope.up_direction # so that >0 means above
        self.info('z position: {} um above floor'.format(position))
