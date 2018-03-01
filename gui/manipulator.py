# coding=utf-8
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

from gui.camera import CameraGui


class ManipulatorGui(CameraGui):

    command_signal = QtCore.pyqtSignal('QString', object)

    def __init__(self, camera, pipette_controller):
        super(ManipulatorGui, self).__init__(camera)
        self.controller = pipette_controller
        self.control_thread = QtCore.QThread()
        self.controller.moveToThread(self.control_thread)
        self.control_thread.start()
        self.controller_signals[self.controller] = self.command_signal
        self.display_edit_funcs.append(self.draw_scale_bar)

    def draw_scale_bar(self, pixmap):
        stage = self.controller.calibrated_stage
        if stage.calibrated:
            barlength = stage.pixel_per_um()[0]*10
            scale = 1.0 * self.camera.width / pixmap.size().width()
            painter = QtGui.QPainter(pixmap)
            pen = QtGui.QPen(QtGui.QColor(200, 0, 0, 125))
            pen.setWidth(4)
            painter.setPen(pen)
            c_x, c_y = pixmap.width() / 20, pixmap.height() * 19.0 / 20
            painter.drawLine(c_x, c_y, c_x + barlength/scale, c_y)
            painter.drawText(c_x, c_y - 10, '10µm')
            painter.end()

    def initialize(self):
        super(ManipulatorGui, self).initialize()
        self.controller.connect(self)

    def register_commands(self):
        super(ManipulatorGui, self).register_commands()

        # Commands to move the stage
        # Note that we do not use the automatic documentation mechanism here,
        # as we one entry for every possible keypress
        for modifier, distance in [(Qt.NoModifier, 10),
                                   (Qt.AltModifier, 2.5),
                                   (Qt.ShiftModifier, 50)]:
            self.register_key_action(Qt.Key_Up, modifier,
                                     self.controller.commands['move_stage_vertical'],
                                     argument=-distance, default_doc=False)
            self.register_key_action(Qt.Key_Down, modifier,
                                     self.controller.commands['move_stage_vertical'],
                                     argument=distance, default_doc=False)
            self.register_key_action(Qt.Key_Left, modifier,
                                     self.controller.commands['move_stage_horizontal'],
                                     argument=-distance, default_doc=False)
            self.register_key_action(Qt.Key_Right, modifier,
                                     self.controller.commands['move_stage_horizontal'],
                                     argument=distance, default_doc=False)

            # Manually document all arrows at once
            if modifier == Qt.NoModifier:
                modifier_text = ''
            else:
                modifier_text = QtGui.QKeySequence(modifier).toString()
            self.help_window.register_custom_action('Stage', modifier_text+'Arrows',
                                                    'Move stage by %gum' % distance)

        # Calibration commands
        self.register_key_action(Qt.Key_C, Qt.ControlModifier,
                                 self.controller.commands['calibrate_stage'],
                                 task_name='Calibrating stage')
        self.register_key_action(Qt.Key_C, Qt.NoModifier,
                                 self.controller.commands['calibrate_manipulator'],
                                 task_name='Calibrating stage and manipulators')
        # Pipette selection
        number_of_units = len(self.controller.calibrated_units)
        for unit_number in range(number_of_units):
            key = QtGui.QKeySequence("%d" % (unit_number + 1))[0]
            self.register_key_action(key, None,
                                     self.controller.commands['switch_manipulator'],
                                     argument=unit_number + 1)

        # Load/save configurations
        # TODO

        # Move pipette by clicking
        self.register_mouse_action(Qt.LeftButton, Qt.NoModifier,
                                   self.controller.commands['move_pipette'])
