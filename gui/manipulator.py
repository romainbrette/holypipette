from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

from gui.camera import CameraGui


class ManipulatorGui(CameraGui):

    command_signal = QtCore.pyqtSignal('QString', object)

    def __init__(self, camera, pipette_controller):
        self.controller = pipette_controller

        super(ManipulatorGui, self).__init__(camera)
        self.control_thread = QtCore.QThread()
        self.controller.moveToThread(self.control_thread)
        self.control_thread.start()
        self.controller_signals[self.controller] = self.command_signal
        self.controller.connect(self)
        self.connect()

    def register_commands(self):
        super(ManipulatorGui, self).register_commands()

        # Commands to move the stage
        for modifier, distance in [(Qt.NoModifier, 10),
                                   (Qt.AltModifier, 2.5),
                                   (Qt.ShiftModifier, 50)]:
            self.register_key_action(Qt.Key_Up, modifier, self.controller, -distance,
                                     'Stage',
                                     'move_stage_vertical',
                                     None, default_doc=False)
            self.register_key_action(Qt.Key_Down, modifier, self.controller, distance,
                                     'Stage',
                                     'move_stage_vertical',
                                     None, default_doc=False)
            self.register_key_action(Qt.Key_Left, modifier, self.controller, -distance,
                                     'Stage',
                                     'move_stage_horizontal',
                                     None, default_doc=False)
            self.register_key_action(Qt.Key_Right, modifier, self.controller, distance,
                                     'Stage',
                                     'move_stage_horizontal',
                                     None, default_doc=False)

            if modifier == Qt.NoModifier:
                modifier_text = ''
            else:
                modifier_text = QtGui.QKeySequence(modifier).toString()
            self.help_window.register_custom_action('Stage', modifier_text+'Arrows',
                                                    'Move stage by %gum' % distance)

        # Calibration commands
        self.register_key_action(Qt.Key_C, Qt.ControlModifier, self.controller, None,
                                 'Stage',
                                 'calibrate_stage',
                                 'Calibrate stage only',
                                 task_name='Calibrating stage')
        self.register_key_action(Qt.Key_C, Qt.NoModifier,
                                 self.controller, None,
                                 'Manipulators',
                                 'calibrate_manipulator',
                                 'Calibrate stage and manipulator')
        # Pipette selection
        number_of_units = len(self.controller.calibrated_units)
        for unit_number in range(number_of_units):
            key = QtGui.QKeySequence("%d" % (unit_number + 1))[0]
            text = 'Switch to manipulator %d' % (unit_number + 1)
            self.register_key_action(key, None, self.controller, unit_number,
                                     'Manipulators',
                                     'switch_manipulator',
                                     text)

        # Load/save configurations
        self.register_key_action(Qt.Key_L, None, self.controller, None,
                                 'Manipulators',
                                 'load_configuration',
                                 'Load previously stored calibration')
        self.register_key_action(Qt.Key_S, None, self.controller, None,
                                 'Manipulators',
                                 'save_configuration',
                                 'Save calibration values')

        # Move pipette by clicking
        self.register_mouse_action(Qt.LeftButton, Qt.NoModifier, self.controller,
                                   'Manipulators',
                                   'move_pipette',
                                   'Move pipette to position')
