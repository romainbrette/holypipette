from __future__ import absolute_import

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from holypipette.controller import Command
from holypipette.executor import TaskExecutor
from holypipette.gui import ConfigGui
from holypipette.gui.manipulator import ManipulatorGui


class PatchGui(ManipulatorGui):

    patch_command_signal = QtCore.pyqtSignal('QString', object)
    patch_reset_signal = QtCore.pyqtSignal(TaskExecutor)

    def __init__(self, camera, pipette_controller, patch_controller):
        super(PatchGui, self).__init__(camera, pipette_controller)
        # Note that pipette controller already runs in a thread, we need to use
        # the same for the patch controller
        self.patch_controller = patch_controller
        self.patch_controller.moveToThread(pipette_controller.thread())
        self.controller_signals[self.patch_controller] = (self.patch_command_signal,
                                                          self.patch_reset_signal)


        self.patch_config_gui = ConfigGui(self.patch_controller.config,
                                          show_name=False)
        self.add_config_gui(self.patch_config_gui,
                            self.patch_controller.config.name)

    def register_commands(self):
        super(PatchGui, self).register_commands()
        self.register_mouse_action(Qt.LeftButton, Qt.ShiftModifier,
                                   self.patch_controller.commands['patch_with_move'],)
        self.register_mouse_action(Qt.LeftButton, Qt.ControlModifier,
                                   self.patch_controller.commands['patch_without_move'])
        self.register_key_action(Qt.Key_B, None,
                                 self.patch_controller.commands['break_in'])

        config_command = Command('patch_config', 'Patch',
                                 'Show/hide the configuration pane')
        self.register_key_action(Qt.Key_P, None, config_command,
                                 func=self.toggle_configuration_display)
