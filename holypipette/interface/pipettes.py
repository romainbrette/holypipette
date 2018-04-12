# coding=utf-8
import pickle
import os

import numpy as np
from PyQt5 import QtCore

from holypipette.interface import TaskInterface
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
        self.calibration_config = CalibrationConfig(name='Calibration config')
        self.calibrated_stage = CalibratedStage(stage, None, microscope, camera,
                                                config=self.calibration_config)
        self.calibrated_units = [CalibratedUnit(unit,
                                                self.calibrated_stage,
                                                microscope,
                                                camera,
                                                config=self.calibration_config)
                                 for unit in units]

        self.controllers.add(self.calibrated_stage)
        for calibrated_unit in self.calibrated_units:
            self.controllers.add(calibrated_unit)

        if config_filename is None:
            config_filename = os.path.join(os.path.expanduser('~'),
                                           'config_manipulator.cfg')
        self.config_filename = config_filename
        self.current_unit = 0
        self.calibrated_unit = None
        self.cleaning_bath_position = None
        self.rinsing_bath_position = None
        # Define commands
        # Stage
        self.add_command('move_stage_vertical', 'Stage',
                         'Move stage vertically by {:.0f}μm',
                         default_arg=10)
        self.add_command('move_stage_horizontal', 'Stage',
                         'Move stage horizontally by {:.0f}μm',
                         default_arg=10)
        self.add_command('calibrate_stage', 'Stage',
                         'Calibrate stage only',
                         task_description='Calibrating stage')
        # Manipulators
        self.add_command('calibrate_manipulator', 'Manipulators',
                         'Calibrate stage and manipulator',
                         task_description='Calibrating stage and manipulator')
        self.add_command('switch_manipulator', 'Manipulators',
                         'Switch to manipulator {}',
                         default_arg=1)
        self.add_command('load_configuration', 'Manipulators',
                         'Load the calibration information for the current '
                         'manipulator')
        self.add_command('save_configuration', 'Manipulators',
                         'Save the calibration information for the current '
                         'manipulator')
        self.add_command('move_pipette', 'Manipulators',
                         'Move pipette to position',
                         task_description='Moving to position with safe approach')
        self.add_command('move_pipette_x', 'Manipulators',
                         'Move pipette in x direction by {:.0f}μm',
                         default_arg=10)
        self.add_command('move_pipette_y', 'Manipulators',
                         'Move pipette in y direction by {:.0f}μm',
                         default_arg=10)
        self.add_command('move_pipette_z', 'Manipulators',
                         'Move pipette in z direction by {:.0f}μm',
                         default_arg=10)
        # Microscope
        self.add_command('move_microscope', 'Microscope',
                         'Move microscope by {:.0f}μm',
                         default_arg=10)
        self.add_command('set_floor', 'Microscope',
                         'Set the position of the floor (cover slip)')
        self.add_command('go_to_floor', 'Microscope',
                         'Go to the floor (cover slip)',
                         task_description='Go to the floor (cover slip)')

    def connect(self, main_gui):
        self.manipulator_switched.connect(main_gui.set_status_message)
        self.switch_manipulator(1)
        # We call this via command_received to catch errors automatically
        self.command_received('load_configuration', None)

    def handle_command(self, command, argument):
        if command == 'move_stage_horizontal':
            self.calibrated_stage.relative_move(argument, axis=0)
        elif command == 'move_stage_vertical':
            self.calibrated_stage.relative_move(argument, axis=1)
        elif command == 'switch_manipulator':
            self.switch_manipulator(argument)
        elif command == 'load_configuration':
            self.load_configuration()
        elif command == 'save_configuration':
            self.save_configuration()
        elif command == 'move_pipette_x':
            self.calibrated_unit.relative_move(argument, axis=0)
        elif command == 'move_pipette_y':
            self.calibrated_unit.relative_move(argument, axis=1)
        elif command == 'move_pipette_z':
            self.calibrated_unit.relative_move(argument, axis=2)
        elif command == 'move_microscope':
            self.microscope.relative_move(argument)
        elif command == 'set_floor':
            self.microscope.floor_Z = self.microscope.position()
        else:
            raise ValueError('Unknown command: %s' % command)

    def handle_blocking_command(self, command, argument):
        if command == 'calibrate_stage':
            if self.execute(self.calibrated_stage, 'calibrate', final_task=False):
                self.execute(self.calibrated_unit, 'analyze_calibration')
        elif command == 'calibrate_manipulator':
            if self.execute(self.calibrated_unit, 'calibrate', final_task=False):
                self.execute(self.calibrated_unit, 'analyze_calibration')
        elif command == 'go_to_floor':
            self.execute(self.microscope, 'absolute_move',
                         x=self.microscope.floor_Z)
        elif command == 'move_pipette':
            self.move_pipette(argument[0], argument[1])
        else:
            raise ValueError('Unknown blocking command: %s' % command)

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

    # TODO: Make the configuration system more general/clean
    def save_configuration(self):
        # Saves configuration
        self.info("Saving configuration")
        cfg = {'stage': self.calibrated_stage.save_configuration(),
               'units': [u.save_configuration() for u in self.calibrated_units],
               'microscope': self.microscope.save_configuration()}
        with open(self.config_filename, "wb") as f:
            pickle.dump(cfg, f)

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

    def move_pipette(self, x, y):
        position = np.array([x, y, self.microscope.position()])
        self.debug('asking for safe move to {}'.format(position))
        self.execute(self.calibrated_unit, 'safe_move', argument=position)
