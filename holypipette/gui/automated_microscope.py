# coding=utf-8
from types import MethodType
import time

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import numpy as np

from holypipette.controller import TaskController
from holypipette.gui import CameraGui
from holypipette.interface import command, blocking_command
import datetime

class AutomatedMicroscopeGui(CameraGui):

    def __init__(self, camera, pipette_interface, with_tracking=False):
        super(AutomatedMicroscopeGui, self).__init__(camera, with_tracking=with_tracking)
        self.setWindowTitle("Automated microscope GUI")
        self.interface = pipette_interface
        self.control_thread = QtCore.QThread()
        self.control_thread.setObjectName('PipetteControlThread')
        self.interface.moveToThread(self.control_thread)
        self.control_thread.start()

        self.add_config_gui(self.interface.config)

        # Stage position for display
        self._last_stage_measurement = None
        self._stage_position = (None, None, None)

    def register_commands(self, manipulator_keys = True):
        super(AutomatedMicroscopeGui, self).register_commands()

        if manipulator_keys:
            # Commands to move the stage
            # Note that we do not use the automatic documentation mechanism here,
            # as we one entry for every possible keypress
            modifiers = [Qt.NoModifier, Qt.AltModifier, Qt.ShiftModifier]
            distances = [10., 2.5, 50.]
            self.help_window.register_custom_action('Stage',  'Arrows',
                                                    'Move stage')
            self.help_window.register_custom_action('Stage',
                                                    '/'.join(QtGui.QKeySequence(mod).toString()
                                                                 if mod is not Qt.NoModifier else 'No modifier'
                                                             for mod in modifiers),
                                                    'Move stage by ' + '/'.join(str(x) for x in distances) + ' µm')

            for modifier, distance in zip(modifiers, distances):
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

        # Microscope control
        self.register_key_action(Qt.Key_PageUp, None,
                                 self.interface.move_microscope,
                                 argument=10, default_doc=False)
        self.register_key_action(Qt.Key_PageDown, None,
                                 self.interface.move_microscope,
                                 argument=-10, default_doc=False)
        key_string = (QtGui.QKeySequence(Qt.Key_PageUp).toString() + '/' +
                      QtGui.QKeySequence(Qt.Key_PageDown).toString())
        self.help_window.register_custom_action('Microscope', key_string,
                                                'Move microscope up/down by 10µm')
        self.register_key_action(Qt.Key_F, None,
                                 self.interface.set_floor)
        self.register_key_action(Qt.Key_G, None,
                                 self.interface.go_to_floor)
        self.register_key_action(Qt.Key_S, None,
                                 self.interface.take_stack)

        # Show configuration pane
        self.register_key_action(Qt.Key_P, None,
                                 self.configuration_keypress)

        # Toggle overlays
        self.register_key_action(Qt.Key_O, None,
                                 self.toggle_overlay)

    def display_timer(self, pixmap):
        interface = self.interface
        painter = QtGui.QPainter(pixmap)
        pen = QtGui.QPen(QtGui.QColor(200, 0, 0, 125))
        pen.setWidth(1)
        painter.setPen(pen)
        c_x, c_y = pixmap.width() / 20, pixmap.height() / 20
        t = int(time.time() - interface.timer_t0)
        hours = t//3600
        minutes = (t-hours*3600)//60
        seconds = t-hours*3600-minutes*60
        painter.drawText(c_x, c_y, '{}'.format(datetime.time(hours,minutes,seconds)))
        painter.end()
