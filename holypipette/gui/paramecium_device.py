'''
GUI for Paramecium electrophysiology
'''
from __future__ import absolute_import

from types import MethodType

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
import numpy as np

from holypipette.controller import TaskController
from holypipette.interface.paramecium_device import ParameciumDeviceInterface
from holypipette.gui.manipulator import ManipulatorGui

#################################################
# Paramecium experiment with the device method #
#################################################
class ParameciumDeviceGui(ManipulatorGui):

    paramecium_command_signal = QtCore.pyqtSignal(MethodType, object)
    paramecium_reset_signal = QtCore.pyqtSignal(TaskController)

    def __init__(self, camera, pipette_interface):
        super(ParameciumDeviceGui, self).__init__(camera,
                                            pipette_interface=pipette_interface,
                                            with_tracking=False)
        self.pipette_interface = pipette_interface
        self.paramecium_interface = ParameciumDeviceInterface(pipette_interface,
                                                        camera)
        self.display_edit_funcs.append(self.display_timer)
        self.paramecium_interface.moveToThread(pipette_interface.thread())
        self.interface_signals[self.paramecium_interface] = (self.paramecium_command_signal,
                                                             self.paramecium_reset_signal)
        self.setWindowTitle("Paramecium device")
        self.add_config_gui(self.paramecium_interface.config)

    def register_commands(self):
        # We have all the commandes of the pipettes interface
        super(ParameciumDeviceGui, self).register_commands(manipulator_keys = False)

        #self.register_mouse_action(Qt.LeftButton, Qt.ShiftModifier,
        #                           self.paramecium_interface.move_pipette_floor) # move to floor level, x axis last
        #self.register_mouse_action(Qt.LeftButton, Qt.ControlModifier,
        #                           self.paramecium_interface.move_pipette_working_level) # move above clicked position

        self.register_key_action(Qt.Key_Space, None,
                                 self.paramecium_interface.move_pipette_down) # move to impalement level
        self.register_key_action(Qt.Key_0, None,
                                 self.pipette_interface.reset_timer)
        self.register_key_action(Qt.Key_Less, None,
                                 self.paramecium_interface.focus_working_level)
        self.register_key_action(Qt.Key_Greater, None,
                                 self.paramecium_interface.focus_calibration_level)
        #self.register_key_action(Qt.Key_At, None,
        #                         self.paramecium_interface.set_center)
        #self.register_key_action(Qt.Key_Home, None,
        #                         self.paramecium_interface.move_to_center)
        self.register_key_action(Qt.Key_Space, Qt.ControlModifier,
                                 self.paramecium_interface.move_pipette_in)
        self.register_key_action(Qt.Key_W, None,
                                 self.paramecium_interface.partial_withdraw)
