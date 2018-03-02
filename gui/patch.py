from PyQt5 import QtCore
from PyQt5.QtCore import Qt

from gui.manipulator import ManipulatorGui


class PatchGui(ManipulatorGui):

    patch_command_signal = QtCore.pyqtSignal('QString', object)

    def __init__(self, camera, pipette_controller, patch_controller):
        super(PatchGui, self).__init__(camera, pipette_controller)
        # Note that pipette controller already runs in a thread, we need to use
        # the same for the patch controller
        self.patch_controller = patch_controller
        self.patch_controller.moveToThread(pipette_controller.thread())
        self.controller_signals[self.patch_controller] = self.patch_command_signal

    def register_commands(self):
        super(PatchGui, self).register_commands()
        self.register_mouse_action(Qt.LeftButton, Qt.ShiftModifier,
                                   self.patch_controller.commands['patch_with_move'])
        self.register_mouse_action(Qt.LeftButton, Qt.ControlModifier,
                                   self.patch_controller.commands['patch_without_move'])
        self.register_key_action(Qt.Key_B, None,
                                 self.patch_controller.commands['break_in'])

    def initialize(self):
        super(PatchGui, self).initialize()
        self.patch_controller.connect(self)