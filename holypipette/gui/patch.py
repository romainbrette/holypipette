from __future__ import absolute_import

from types import MethodType

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from holypipette.controller import TaskController
from holypipette.gui.manipulator import ManipulatorGui


class PatchGui(ManipulatorGui):

    patch_command_signal = QtCore.pyqtSignal(MethodType, object)
    patch_reset_signal = QtCore.pyqtSignal(TaskController)

    def __init__(self, camera, pipette_interface, patch_interface,
                 with_tracking=False):
        super(PatchGui, self).__init__(camera, pipette_interface,
                                       with_tracking=with_tracking)
        self.setWindowTitle("Patch GUI")
        # Note that pipette interface already runs in a thread, we need to use
        # the same for the patch interface
        self.patch_interface = patch_interface
        self.patch_interface.moveToThread(pipette_interface.thread())
        self.interface_signals[self.patch_interface] = (self.patch_command_signal,
                                                        self.patch_reset_signal)
        self.add_config_gui(self.patch_interface.config)

    def register_commands(self):
        super(PatchGui, self).register_commands()
        self.register_mouse_action(Qt.LeftButton, Qt.ShiftModifier,
                                   self.patch_interface.patch_with_move)
        self.register_mouse_action(Qt.LeftButton, Qt.ControlModifier,
                                   self.patch_interface.patch_without_move)
        self.register_key_action(Qt.Key_B, None,
                                 self.patch_interface.break_in)
        self.register_key_action(Qt.Key_F3, None,
                                 self.patch_interface.store_cleaning_position)
        self.register_key_action(Qt.Key_F4, None,
                                 self.patch_interface.store_rinsing_position)
        self.register_key_action(Qt.Key_F5, None,
                                 self.patch_interface.clean_pipette)


class TrackingPatchGui(PatchGui):

    def __init__(self, camera, pipette_interface, patch_interface,
                 with_tracking=False):
        super(TrackingPatchGui, self).__init__(camera, pipette_interface,
                                               patch_interface,
                                               with_tracking=True)
        self.setWindowTitle("Patch GUI with tracking")

    def register_commands(self):
        super(TrackingPatchGui, self).register_commands()
        self.register_key_action(Qt.Key_F2, None,
                                 self.patch_interface.sequential_patching)
        self.register_mouse_action(Qt.RightButton, None,
                                   self.camera_interface.track_object)
