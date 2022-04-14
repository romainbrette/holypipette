# coding=utf-8
import pickle
import os
import yaml

import numpy as np
from PyQt5 import QtCore

from holypipette.interface import TaskInterface, command, blocking_command
from holypipette.devices.manipulator.calibratedunit import *
import time

class PipetteInterface(TaskInterface):
    '''
    Controller for the stage, the microscope, and several pipettes.
    '''

    manipulator_switched = QtCore.pyqtSignal('QString', 'QString')

    def __init__(self, stage, microscope, camera, units,
                 config_filename=None):
        super(PipetteInterface, self).__init__()
        # Create a common calibration configuration for all stages/manipulators
        self.calibration_config = CalibrationConfig(name='Calibration')

        # This should be refactored (in TaskInterface?)
        config_folder = os.path.join(os.path.expanduser('~'),'holypipette')
        if not os.path.exists(config_folder):
            os.mkdir(config_folder)
        if config_filename is None:
            config_filename = 'config_manipulator.cfg'
        config_filename = os.path.join(config_folder,config_filename)
        self.config_filename = config_filename

        # Load stage and manipulator configuration
        filename = os.path.join(config_folder, 'configuration.yaml')
        with open(filename, 'r') as f:
            manip_config = yaml.safe_load(f)

        self.microscope = CalibratedMicroscope(microscope, config=self.calibration_config,
                                               direction=manip_config['microscope']['direction'])
        self.camera = CalibratedCamera(camera)
        self.calibrated_stage = CalibratedStage(stage, None, self.microscope, self.camera,
                                                config=self.calibration_config,
                                                direction=manip_config['stage']['direction'])
        self.calibrated_units = []
        for i, unit in enumerate(units):
            CalibratedUnit(unit, self.calibrated_stage, self.microscope, self.camera,
                           config=self.calibration_config,
                           direction=manip_config['manipulators'][i]['direction'],
                           alpha=manip_config['manipulators'][i]['alpha'],
                           theta=manip_config['manipulators'][i]['theta'])

        self.current_unit = 0
        self.calibrated_unit = None
        self.timer_t0 = time.time()

        self.calibration_started = False
        self.previous_position = None

    def connect(self, main_gui):
        self.manipulator_switched.connect(main_gui.set_status_message)
        self.switch_manipulator(1)
        # We call this via command_received to catch errors automatically
        self.command_received(self.load_configuration, None)

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
        #self.manipulator_switched.emit('Manipulators',
        #                               'Manipulator: %d' % unit_number)


    @blocking_command(category='Stage',
                      description='Zero position',
                      task_description='Setting zero position')
    def zero_position(self):
        self.execute([self.calibrated_stage.recalibrate,
                      self.microscope.recalibrate])

    @blocking_command(category='Manipulators',
                      description='Calibrate manipulator',
                      task_description='Calibrating manipulator')
    def calibrate_manipulator(self):
        if self.calibration_started:
            self.execute(self.calibrated_unit.measure_theta, argument=self.previous_position)
        else:
            self.previous_position = self.calibrated_unit.position()
        self.calibration_started = not self.calibration_started

    @blocking_command(category='Manipulators',
                      description='Recalibrate manipulator',
                      task_description='Recalibrating manipulator')
    def recalibrate_manipulator(self):
        self.execute(self.calibrated_unit.recalibrate)

    @blocking_command(category='Manipulators',
                     description='Recalibrate manipulator',
                     task_description='Recalibrate manipulator at click position')
    def recalibrate_manipulator_on_click(self, xy_position):
        self.debug('asking for recalibration at {}'.format(xy_position))
        self.execute(self.calibrated_unit.recalibrate, argument=xy_position)

    @blocking_command(category='Manipulators',
                     description='Move pipette to position',
                     task_description='Moving to position with safe approach')
    def move_pipette(self, xy_position):
        x, y = xy_position
        position = np.array([x, y, self.microscope.reference_position()])
        self.debug('asking for safe move to {}'.format(position))
        self.execute(self.calibrated_unit.safe_move, argument=position)

    @blocking_command(category='Manipulators',
                     description='Move stage to position',
                     task_description='Moving stage to position')
    def move_stage(self, xy_position):
        x, y = xy_position
        position = np.array([x, y])
        self.debug('asking for reference move to {}'.format(position))
        self.execute(self.calibrated_stage.reference_relative_move, argument=-position) # compensatory move

    @blocking_command(category='Microscope',
                      description='Go to the floor (cover slip)',
                      task_description='Go to the floor (cover slip)')
    def go_to_floor(self):
        self.execute(self.microscope.absolute_move,
                     argument=0)

    # TODO: Make the configuration system more general/clean
    @command(category='Manipulators',
             description='Save the calibration information',
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
             description='Load the calibration information',
             success_message='Calibration information loaded')
    def load_configuration(self):
        # Loads configuration
        self.info("Loading configuration")
        if os.path.exists(self.config_filename):
            with open(self.config_filename, "rb") as f:
                cfg = pickle.load(f)
                self.microscope.load_configuration(cfg['microscope'])
                self.calibrated_stage.load_configuration(cfg['stage'])
                cfg_units = cfg['units']
                for i, cfg_unit in enumerate(cfg_units):
                    self.calibrated_units[i].load_configuration(cfg_unit)
                self.calibrated_unit.analyze_calibration()
        else:
            self.debug('Configuration file {} not found'.format(self.config_filename))

    @command(category='Manipulators',
                     description='Reset timer')
    def reset_timer(self):
        self.timer_t0 = time.time()
