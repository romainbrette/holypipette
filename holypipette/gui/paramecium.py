'''
GUI for Paramecium electrophysiology
'''
from __future__ import absolute_import

from types import MethodType

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from holypipette.controller import TaskController
from holypipette.gui.manipulator import ManipulatorGui

class ParameciumGui(ManipulatorGui):

    def __init__(self, camera, pipette_interface):
        super(ParameciumGui, self).__init__(camera, pipette_interface,
                                       with_tracking=False)
        self.setWindowTitle("Paramecium GUI")
        #self.add_config_gui(self.patch_interface.config)

    def register_commands(self):
        super(ParameciumGui, self).register_commands()
