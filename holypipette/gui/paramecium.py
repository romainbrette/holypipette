'''
GUI for Paramecium electrophysiology
'''
from __future__ import absolute_import

from types import MethodType

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from holypipette.controller import TaskController
from holypipette.interface.paramecium import ParameciumInterface
from holypipette.gui.manipulator import ManipulatorGui

class ParameciumGui(ManipulatorGui):

    paramecium_command_signal = QtCore.pyqtSignal(MethodType, object)
    paramecium_reset_signal = QtCore.pyqtSignal(TaskController)

    def __init__(self, camera, pipette_interface):
        super(ParameciumGui, self).__init__(camera,
                                            pipette_interface=pipette_interface,
                                            with_tracking=False)
        self.paramecium_interface = ParameciumInterface(pipette_interface)
        self.paramecium_interface.moveToThread(pipette_interface.thread())
        self.interface_signals[self.paramecium_interface] = (self.paramecium_command_signal,
                                                             self.paramecium_reset_signal)
        self.setWindowTitle("Paramecium GUI")
        self.add_config_gui(self.paramecium_interface.config)

    def register_commands(self):
        super(ParameciumGui, self).register_commands()

        self.register_mouse_action(Qt.LeftButton, Qt.ShiftModifier,
                                   self.paramecium_interface.move_pipette_down)
        '''
        self.register_key_action(Qt.Key_F5, None,
                                 self.paramecium_interface.store_paramecium_position)
        self.register_key_action(Qt.Key_F6, None,
                                 self.paramecium_interface.microdroplet_making)
        self.register_key_action(Qt.Key_F7, None,
                                 self.paramecium_interface.paramecium_movement)
        self.register_key_action(Qt.Key_F9, None,
                                 self.paramecium_interface.paramecium_catching)
        '''
