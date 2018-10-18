# coding=utf-8
import pickle
import os

import numpy as np
from PyQt5 import QtCore

from holypipette.interface import TaskInterface, command, blocking_command
from holypipette.devices.manipulator.calibratedunit import CalibratedUnit, CalibratedStage, CalibrationConfig


class PipetteInterface(TaskInterface):
    '''
    Controller for the stage, the microscope, and several pipettes.
    '''

    manipulator_switched = QtCore.pyqtSignal('QString', 'QString')

    def __init__(self, stage, microscope, camera, units,
                 config_filename=None):
        super(PipetteInterface, self).__init__()
        self.microscope = microscope
        self.camera = camera
        # Create a common calibration configuration for all stages/manipulators
        self.calibration_config = CalibrationConfig(name='Calibration')
        self.calibrated_stage = CalibratedStage(stage, None, microscope, camera,
                                                config=self.calibration_config)
        self.calibrated_units = [CalibratedUnit(unit,
                                                self.calibrated_stage,
                                                microscope,
                                                camera,
                                                config=self.calibration_config)
                                 for unit in units]

        if config_filename is None:
            config_filename = os.path.join(os.path.expanduser('~'),
                                           'config_manipulator.cfg')
        self.config_filename = config_filename
        self.current_unit = 0
        self.calibrated_unit = None
        self.cleaning_bath_position = None
        self.contact_position = None
        self.rinsing_bath_position = None
        self.paramecium_tank_position = None

    def connect(self, main_gui):
        self.manipulator_switched.connect(main_gui.set_status_message)
        self.switch_manipulator(1)
        # We call this via command_received to catch errors automatically
        self.command_received(self.load_configuration, None)

    @command(category='Manipulators',
             description='Measure manipulator ranges')
    def measure_ranges(self):
        for calibrated_unit in self.calibrated_units:
            position = calibrated_unit.position()
            calibrated_unit.min = np.array([position,calibrated_unit.min]).min(axis=0)
            calibrated_unit.max = np.array([position,calibrated_unit.max]).max(axis=0)
        position = self.calibrated_stage.position()
        self.calibrated_stage.min = np.array([position, self.calibrated_stage.min]).min(axis=0)
        self.calibrated_stage.max = np.array([position, self.calibrated_stage.max]).max(axis=0)
        position = self.microscope.position()
        self.microscope.min = min(self.microscope.min, position)
        self.microscope.max = max(self.microscope.max, position)

    @command(category='Manipulators',
             description='Reset manipulator ranges')
    def reset_ranges(self):
        for calibrated_unit in self.calibrated_units:
            calibrated_unit.min = np.ones(len(calibrated_unit.min))*1e6
            calibrated_unit.max = -np.ones(len(calibrated_unit.max))*1e6
        self.calibrated_stage.min = np.ones(len(self.calibrated_stage.min))*1e6
        self.calibrated_stage.max = -np.ones(len(self.calibrated_stage.max))*1e6
        self.microscope.min = 1e6
        self.microscope.max = -1e6

    @command(category='Manipulators',
             description='Check manipulator ranges')
    def check_ranges(self):
        for i,calibrated_unit in enumerate(self.calibrated_units):
            print(calibrated_unit.min,calibrated_unit.max)
            if ((calibrated_unit.max-calibrated_unit.min)<500.).any():
                self.debug("Ranges of unit "+str(i)+" might not have been updated")
        print(self.calibrated_stage.min,self.calibrated_stage.max)
        if ((self.calibrated_stage.max - self.calibrated_stage.min) < 500.).any():
            self.debug("Ranges of the stage might not have been updated")
        print(self.microscope.min,self.microscope.max)
        if self.microscope.max-self.microscope.min<500.:
            self.debug("Ranges of the microscope might not have been updated")

    @command(category='Manipulators',
             description='Move pipette in x direction by {:.0f}μm',
             default_arg=10)
    def move_pipette_x(self, distance):
        self.calibrated_unit.relative_move(distance, axis=0)

    @command(category='Manipulators',
             description='Move pipette in y direction by {:.0f}μm',
             default_arg=10)
    def move_pipette_y(self, distance):
        self.calibrated_unit.relative_move(distance, axis=1)

    @command(category='Manipulators',
             description='Move pipette in z direction by {:.0f}μm',
             default_arg=10)
    def move_pipette_z(self, distance):
        self.calibrated_unit.relative_move(distance, axis=2)

    @command(category='Microscope',
             description='Move microscope by {:.0f}μm',
             default_arg=10)
    def move_microscope(self, distance):
        self.microscope.relative_move(distance)

    @command(category='Microscope',
             description='Set the position of the floor (cover slip)',
             success_message='Cover slip position stored')
    def set_floor(self):
        self.microscope.floor_Z = self.microscope.position()

    @command(category='Stage',
             description='Move stage vertically by {:.0f}μm',
             default_arg=10)
    def move_stage_vertical(self, distance):
        self.calibrated_stage.relative_move(distance, axis=1)

    @command(category='Stage',
             description='Move stage horizontally by {:.0f}μm',
             default_arg=10)
    def move_stage_horizontal(self, distance):
        self.calibrated_stage.relative_move(distance, axis=0)

    @command(category='Manipulators',
             description='Switch to manipulator {}',
             default_arg=1)
    def switch_manipulator(self, unit_number):
        '''
        Switch the currently active manipulator

        Parameters
        ----------
        unit_number : int
            The number of the manipulator (using 1-based indexing, whereas the
            code internally uses 0-based indexing).
        '''
        self.current_unit = unit_number - 1
        self.calibrated_unit = self.calibrated_units[self.current_unit]
        self.manipulator_switched.emit('Manipulators',
                                       'Manipulator: %d' % unit_number)


    @blocking_command(category='Stage',
                      description='Calibrate stage only',
                      task_description='Calibrating stage')
    def calibrate_stage(self):

        print("hello")

        if self.execute(self.calibrated_stage, 'calibrate', final_task=False):
            self.execute(self.calibrated_unit, 'analyze_calibration')

    @blocking_command(category='Manipulators',
                      description='Calibrate stage and manipulator',
                      task_description='Calibrating stage and manipulator')
    def calibrate_manipulator(self):
        if self.execute(self.calibrated_unit, 'calibrate', final_task=False):
            self.execute(self.calibrated_unit, 'analyze_calibration')

    @blocking_command(category='Manipulators',
                      description='Calibrate stage and manipulator (2nd Method)',
                      task_description='Calibrating stage and manipulator (2nd Method)')
    def calibrate_manipulator2(self):
        if self.execute(self.calibrated_unit, 'calibrate', argument = 2, final_task=False):
            self.execute(self.calibrated_unit, 'analyze_calibration')

    @blocking_command(category='Manipulators',
                      description='Recalibrate stage and manipulator',
                      task_description='Recalibrating stage and manipulator')
    def recalibrate_manipulator(self):
        self.execute(self.calibrated_unit, 'recalibrate')

    @blocking_command(category='Manipulators',
                     description='Recalibrate manipulator',
                     task_description='Recalibrate manipulator at click position')
    def recalibrate_manipulator_on_click(self, xy_position):
        self.debug('asking for recalibration at {}'.format(xy_position))
        self.execute(self.calibrated_unit, 'recalibrate', argument=xy_position)

    @blocking_command(category='Manipulators',
                     description='Move pipette to position',
                     task_description='Moving to position with safe approach')
    def move_pipette(self, xy_position):
        x, y = xy_position
        position = np.array([x, y, self.microscope.position()])
        self.debug('asking for safe move to {}'.format(position))
        self.execute(self.calibrated_unit, 'safe_move', argument=position)

    @blocking_command(category='Microscope',
                      description='Go to the floor (cover slip)',
                      task_description='Go to the floor (cover slip)')
    def go_to_floor(self):
        self.execute(self.microscope, 'absolute_move',
                     argument=self.microscope.floor_Z)

    # TODO: Make the configuration system more general/clean
    @command(category='Manipulators',
             description='Save the calibration information for the current manipulator',
             success_message='Calibration information stored')
    def save_configuration(self):
        # Saves configuration
        self.info("Saving configuration")
        cfg = {'stage': self.calibrated_stage.save_configuration(),
               'units': [u.save_configuration() for u in self.calibrated_units],
               'microscope': self.microscope.save_configuration()}
        with open(self.config_filename, "wb") as f:
            pickle.dump(cfg, f)

    @command(category='Manipulators',
             description='Load the calibration information for the current manipulator',
             success_message='Calibration information loaded')
    def load_configuration(self):
        # Loads configuration
        self.info("Loading configuration")
        with open(self.config_filename, "rb") as f:
            cfg = pickle.load(f)
            self.microscope.load_configuration(cfg['microscope'])
            self.calibrated_stage.load_configuration(cfg['stage'])
            cfg_units = cfg['units']
            for i, cfg_unit in enumerate(cfg_units):
                self.calibrated_units[i].load_configuration(cfg_unit)
            self.calibrated_unit.analyze_calibration()

