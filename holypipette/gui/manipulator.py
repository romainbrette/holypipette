# coding=utf-8
from types import MethodType

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
import numpy as np

from holypipette.controller import TaskController
from holypipette.gui import CameraGui
from holypipette.interface import command


class ManipulatorGui(CameraGui):

    pipette_command_signal = QtCore.pyqtSignal(MethodType, object)
    pipette_reset_signal = QtCore.pyqtSignal(TaskController)

    def __init__(self, camera, pipette_interface, with_tracking=False):
        super(ManipulatorGui, self).__init__(camera, with_tracking=with_tracking)
        self.setWindowTitle("Pipette GUI")
        self.interface = pipette_interface
        self.control_thread = QtCore.QThread()
        self.control_thread.setObjectName('PipetteControlThread')
        self.interface.moveToThread(self.control_thread)
        self.control_thread.start()
        self.interface_signals[self.interface] = (self.pipette_command_signal,
                                                  self.pipette_reset_signal)
        self.display_edit_funcs.append(self.draw_scale_bar)
        self.add_config_gui(self.interface.calibration_config)

        # Measure manipulator positions
        self.position_timer = QtCore.QTimer()
        self.position_timer.timeout.connect(self.interface.measure_ranges)
        self.position_measurement = False

    @command(category='Manipulators',
             description='Measure manipulator ranges')
    def measure_ranges(self):
        if self.position_measurement is False:
            self.position_measurement = True
            # Reset ranges
            self.interface.reset_ranges()
            self.position_timer.start(500)
        else:
            self.position_measurement = False
            self.position_timer.stop()
            # Check whether all positions have been updated
            self.interface.check_ranges()

    def draw_scale_bar(self, pixmap, text=True, autoscale=True,
                       position=True):
        if autoscale and not text:
            raise ValueError('Automatic scaling of the bar without showing text '
                             'will not be very helpful...')
        stage = self.interface.calibrated_stage
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
            if position:
                x = stage.position(axis=0)
                y = stage.position(axis=1)
                z = self.interface.microscope.position()
                position_text = 'x: {:.0f}µm, y: {:.0f}µm, z: {:.0f}µm'
                painter.drawText(c_x, c_y + 20, position_text.format(x, y, z))
            painter.end()

    def register_commands(self):
        super(ManipulatorGui, self).register_commands()

        # Commands to move the stage
        # Note that we do not use the automatic documentation mechanism here,
        # as we one entry for every possible keypress
        for modifier, distance in [(Qt.NoModifier, 10),
                                   (Qt.AltModifier, 2.5),
                                   (Qt.ShiftModifier, 50)]:
            self.register_key_action(Qt.Key_Up, modifier,
                                     self.interface.move_stage_vertical,
                                     argument=-distance, default_doc=False)
            self.register_key_action(Qt.Key_Down, modifier,
                                     self.interface.move_stage_vertical,
                                     argument=distance, default_doc=False)
            self.register_key_action(Qt.Key_Left, modifier,
                                     self.interface.move_stage_horizontal,
                                     argument=-distance, default_doc=False)
            self.register_key_action(Qt.Key_Right, modifier,
                                     self.interface.move_stage_horizontal,
                                     argument=distance, default_doc=False)
            self.register_key_action(Qt.Key_W, modifier,
                                     self.interface.move_pipette_y,
                                     argument=distance, default_doc=False)
            self.register_key_action(Qt.Key_S, modifier,
                                     self.interface.move_pipette_y,
                                     argument=-distance, default_doc=False)
            self.register_key_action(Qt.Key_A, modifier,
                                     self.interface.move_pipette_x,
                                     argument=distance, default_doc=False)
            self.register_key_action(Qt.Key_D, modifier,
                                     self.interface.move_pipette_x,
                                     argument=-distance, default_doc=False)
            self.register_key_action(Qt.Key_Q, modifier,
                                     self.interface.move_pipette_z,
                                     argument=distance, default_doc=False)
            self.register_key_action(Qt.Key_E, modifier,
                                     self.interface.move_pipette_z,
                                     argument=-distance, default_doc=False)

            # Manually document all arrows at once
            if modifier == Qt.NoModifier:
                modifier_text = ''
            else:
                modifier_text = QtGui.QKeySequence(modifier).toString()
            self.help_window.register_custom_action('Stage', modifier_text+'Arrows',
                                                    'Move stage by %gum' % distance)
            self.help_window.register_custom_action('Manipulators', modifier_text+'A/S/W/D',
                                                    'Move pipette by %gum in x/y direction' % distance)
            self.help_window.register_custom_action('Manipulators', modifier_text+'Q/E',
                                                    'Move pipette by %gum in z direction' % distance)

        # Calibration commands
        self.register_key_action(Qt.Key_C, Qt.ControlModifier,
                                 self.interface.calibrate_stage)
        self.register_key_action(Qt.Key_C, Qt.NoModifier,
                                 self.interface.calibrate_manipulator)
        self.register_key_action(Qt.Key_C, Qt.AltModifier,
                                 self.interface.calibrate_manipulator2)
        self.register_key_action(Qt.Key_R, Qt.NoModifier,
                                 self.interface.recalibrate_manipulator)
        self.register_mouse_action(Qt.RightButton, Qt.NoModifier,
                                   self.interface.recalibrate_manipulator_on_click)
        self.register_key_action(Qt.Key_M, Qt.NoModifier,
                                 self.measure_ranges)
        # Pipette selection
        number_of_units = len(self.interface.calibrated_units)
        for unit_number in range(number_of_units):
            key = QtGui.QKeySequence("%d" % (unit_number + 1))[0]
            self.register_key_action(key, None,
                                     self.interface.switch_manipulator,
                                     argument=unit_number + 1)

        self.register_key_action(Qt.Key_S, Qt.ControlModifier,
                                 self.interface.save_configuration)

        # Move pipette by clicking
        self.register_mouse_action(Qt.LeftButton, Qt.NoModifier,
                                   self.interface.move_pipette)

        # Microscope control
        self.register_key_action(Qt.Key_PageUp, None,
                                 self.interface.move_microscope,
                                 argument=10)
        self.register_key_action(Qt.Key_PageDown, None,
                                 self.interface.move_microscope,
                                 argument=-10)
        self.register_key_action(Qt.Key_F, None,
                                 self.interface.set_floor)
        self.register_key_action(Qt.Key_G, None,
                                 self.interface.go_to_floor)

        # Show configuration pane
        self.register_key_action(Qt.Key_P, None,
                                 self.configuration_keypress)

