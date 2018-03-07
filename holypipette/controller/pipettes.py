import cPickle as pickle
import os

import numpy as np
from PyQt5 import QtCore

from holypipette.controller import TaskController
from holypipette.devices.manipulator.calibratedunit import CalibratedUnit, CalibratedStage


class PipetteController(TaskController):
    '''
    Controller for the stage, the microscope, and several pipettes.
    '''

    manipulator_switched = QtCore.pyqtSignal('QString', 'QString')

    def __init__(self, stage, microscope, camera, units,
                 config_filename=None):
        super(PipetteController, self).__init__()
        self.microscope = microscope
        self.camera = camera
        self.calibrated_stage = CalibratedStage(stage, None, microscope, camera)
        self.calibrated_units = [CalibratedUnit(unit,
                                                self.calibrated_stage,
                                                microscope,
                                                camera)
                                 for unit in units]

        self.executors.add(self.calibrated_stage)
        for calibrated_unit in self.calibrated_units:
            self.executors.add(calibrated_unit)


        if config_filename is None:
            config_filename = os.path.join(os.path.expanduser('~'),
                                           'config_manipulator.cfg')
        self.config_filename = config_filename
        self.current_unit = 0
        self.calibrated_unit = None

        # Define commands
        self.add_command('move_stage_vertical', 'Stage',
                         'Move stage vertically by {:.0f}um',
                         default_arg=10)
        self.add_command('move_stage_horizontal', 'Stage',
                         'Move stage horizontally by {:.0f}um',
                         default_arg=10)
        self.add_command('calibrate_stage', 'Stage',
                         'Calibrate stage only',
                         task_description='Calibrating stage')
        self.add_command('calibrate_manipulator', 'Manipulators',
                         'Calibrate stage and manipulator',
                         task_description='Calibrating stage and manipulator')
        self.add_command('switch_manipulator', 'Manipulators',
                         'Switch to manipulator {}',
                         default_arg=1)
        self.add_command('load_configuration', 'Manipulators',
                         'Load the calibration information for the current manipulator')
        self.add_command('save_configuration', 'Manipulators',
                         'Save the calibration information for the current manipulator')
        self.add_command('move_pipette', 'Manipulators',
                         'Move pipette to position')

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
        elif command == 'move_pipette':
            self.move_pipette(argument[0], argument[1])
        else:
            raise ValueError('Unknown command: %s' % command)

    def handle_blocking_command(self, command, argument):
        if command == 'calibrate_stage':
            self.execute(self.calibrated_stage, 'calibrate', final_task=False)
            self.execute(self.calibrated_unit, 'analyze_calibration')
        elif command == 'calibrate_manipulator':
            self.execute(self.calibrated_unit, 'calibrate', final_task=False)
            self.execute(self.calibrated_unit, 'analyze_calibration')
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
        self.calibrated_unit.run('safe_move', position)
