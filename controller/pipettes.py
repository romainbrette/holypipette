import cPickle as pickle
import os

import numpy as np
from PyQt5 import QtCore

from devices.manipulator.calibratedunit import CalibratedUnit, CalibratedStage

def message(msg):
    print(msg)


class PipetteController(QtCore.QObject):
    '''
    Controller for the stage, the microscope, and several pipettes.
    '''

    manipulator_switched = QtCore.pyqtSignal('QString', 'QString')
    task_finished = QtCore.pyqtSignal(int)

    def __init__(self, stage, microscope, camera, units,
                 config_filename=None):
        super(PipetteController, self).__init__()
        self.microscope = microscope
        self.camera = camera
        self.calibrated_stage = CalibratedStage(stage, None, microscope, camera,
                                                parent=self)
        self.calibrated_units = [CalibratedUnit(unit,
                                                self.calibrated_stage,
                                                microscope,
                                                camera)
                                 for unit in units]
        if config_filename is None:
            config_filename = os.path.join(os.path.expanduser('~'),
                                           'config_manipulator.cfg')
        self.config_filename = config_filename
        self.current_unit = 0
        self.calibrated_unit = None

    def connect(self, main_gui):
        self.manipulator_switched.connect(main_gui.set_status_message)
        self.switch_manipulator(0)
        # We call this via handle command to catch errors automatically
        self.handle_command('load_configuration', None)
        self.task_finished.connect(main_gui.task_finished)

    @QtCore.pyqtSlot('QString', object)
    def handle_command(self, command, argument):
        if command == 'move_stage_horizontal':
            self.calibrated_stage.relative_move(argument, axis=0)
        elif command == 'move_stage_vertical':
            self.calibrated_stage.relative_move(argument, axis=1)
        elif command == 'calibrate_stage':
            self.calibrate_stage()
        elif command == 'calibrate_manipulator':
            self.calibrate()
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

    def abort_task(self):
        self.calibrated_stage.abort_requested = True
        for calibrated_unit in self.calibrated_units:
            calibrated_unit.abort_requested = True

    def switch_manipulator(self, unit_number):
        self.current_unit = unit_number
        self.calibrated_unit = self.calibrated_units[self.current_unit]
        self.manipulator_switched.emit('Manipulators',
                                       'Manipulator: %d' % (self.current_unit + 1))

    def calibrate(self):
        self.calibrated_unit.calibrate(message)
        self.calibrated_unit.analyze_calibration()

    def calibrate_stage(self):
        self.calibrated_stage.run('calibrate')
        if self.calibrated_stage.error:
            self.task_finished.emit(1)
        elif self.calibrated_stage.abort_requested:
            self.task_finished.emit(2)
        else:
            self.calibrated_unit.run('analyze_calibration')
            self.task_finished.emit(0)

    # TODO: Make the configuration system more general/clean
    def save_configuration(self):
        # Saves configuration
        print("Saving configuration")
        cfg = {'stage': self.calibrated_stage.save_configuration(),
               'units': [u.save_configuration() for u in self.calibrated_units],
               'microscope': self.microscope.save_configuration()}
        with open(self.config_filename, "wb") as f:
            pickle.dump(cfg, f)

    def load_configuration(self):
        # Loads configuration
        print("Loading configuration")
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
