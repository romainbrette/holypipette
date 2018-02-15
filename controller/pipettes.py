import cPickle as pickle
import os

from PyQt5 import QtCore

from devices.manipulator.calibratedunit import CalibratedUnit, CalibratedStage

def message(msg):
    print(msg)

class PipetteController(QtCore.QObject):
    '''
    Controller for the stage, the microscope, and several pipettes.
    '''

    manipulator_switched = QtCore.pyqtSignal('QString', 'QString')

    def __init__(self, stage, microscope, camera, units,
                 config_filename=None):
        super(PipetteController, self).__init__()
        self.stage = stage
        self.microscope = microscope
        self.camera = camera
        self.units = units
        self.calibrated_stage = CalibratedStage(stage, None, microscope, camera)
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
        # We call this via handle command to catch errors automatically
        self.handle_command('load_configuration', None)

    def connect(self, main_gui):
        self.manipulator_switched.connect(main_gui.set_status_message)
        self.switch_manipulator(0)

    @QtCore.pyqtSlot('QString', object)
    def handle_command(self, command, argument):
        #TODO: Move error handling into a reusable function
        try:
            if command == 'move_stage_horizontal':
                self.stage.relative_move(argument, axis=0)
            elif command == 'move_stage_vertical':
                self.stage.relative_move(argument, axis=1)
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
            else:
                raise ValueError('Unknown command: %s' % command)
        except Exception as ex:
            # TODO: Use a logging object provided by the main GUI and/or have
            # an error signal
            print('An exception occured: %s' % str(ex))

    def switch_manipulator(self, unit_number):
        self.current_unit = unit_number
        self.calibrated_unit = self.calibrated_units[self.current_unit]
        self.manipulator_switched.emit('Manipulators',
                                       'Manipulator: %d' % (self.current_unit + 1))

    def calibrate(self):
        self.calibrated_unit.calibrate(message)
        self.calibrated_unit.analyze_calibration()

    def calibrate_stage(self):
        self.calibrated_stage.calibrate(message)
        self.calibrated_unit.analyze_calibration()

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