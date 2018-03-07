# coding=utf-8
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
import numpy as np

from holypipette.executor import TaskExecutor
from holypipette.gui import CameraGui


class ManipulatorGui(CameraGui):

    pipette_command_signal = QtCore.pyqtSignal('QString', object)
    pipette_reset_signal = QtCore.pyqtSignal(TaskExecutor)

    def __init__(self, camera, pipette_controller):
        super(ManipulatorGui, self).__init__(camera)
        self.controller = pipette_controller
        self.control_thread = QtCore.QThread()
        self.control_thread.setObjectName('PipetteControlThread')
        self.controller.moveToThread(self.control_thread)
        self.control_thread.start()
        self.controller_signals[self.controller] = (self.pipette_command_signal,
                                                    self.pipette_reset_signal)
        self.display_edit_funcs.append(self.draw_scale_bar)

    def draw_scale_bar(self, pixmap, text=True, autoscale=True):
        if autoscale and not text:
            raise ValueError('Automatic scaling of the bar without showing text '
                             'will not be very helpful...')
        stage = self.controller.calibrated_stage
        if stage.calibrated:
            pen_width = 4
            bar_length = stage.pixel_per_um()[0]
            scale = 1.0 * self.camera.width / pixmap.size().width()
            scaled_length = bar_length/scale
            if autoscale:
                lengths = np.array([1, 2, 5, 10, 20, 50, 100])
                if scaled_length*lengths[-1] < pen_width:
                    # even the longest bar is not long enough -- don't show
                    # any scale bar
                    return
                elif scaled_length*lengths[0] > 20*pen_width:
                    # the shortest bar is not short enough (>20x the width)
                    length_in_um = lengths[0]
                else:
                    # Use the length that gives a bar of about 10x its width
                    length_in_um = lengths[np.argmin(np.abs(scaled_length*lengths - 10*pen_width))]
            else:
                length_in_um = 10

            painter = QtGui.QPainter(pixmap)
            pen = QtGui.QPen(QtGui.QColor(200, 0, 0, 125))
            pen.setWidth(pen_width)
            painter.setPen(pen)
            c_x, c_y = pixmap.width() / 20, pixmap.height() * 19.0 / 20
            painter.drawLine(c_x, c_y,
                             int(c_x + round(length_in_um*scaled_length)), c_y)
            if text:
                painter.drawText(c_x, c_y - 10, '{}µm'.format(length_in_um))
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
                                 self.controller.commands['calibrate_stage'])
        self.register_key_action(Qt.Key_C, Qt.NoModifier,
                                 self.controller.commands['calibrate_manipulator'])
        # Pipette selection
        number_of_units = len(self.controller.calibrated_units)
        for unit_number in range(number_of_units):
            key = QtGui.QKeySequence("%d" % (unit_number + 1))[0]
            self.register_key_action(key, None,
                                     self.controller.commands['switch_manipulator'],
                                     argument=unit_number + 1)

        self.register_key_action(Qt.Key_S, None,
                                 self.controller.commands['save_configuration'])

        # Move pipette by clicking
        self.register_mouse_action(Qt.LeftButton, Qt.NoModifier,
                                   self.controller.commands['move_pipette'])
