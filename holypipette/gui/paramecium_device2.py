'''
Simplified Paramecium device GUI

GUI for Paramecium electrophysiology, with the immobilization device
'''
from __future__ import absolute_import

from PyQt5.QtCore import Qt
from holypipette.gui.manipulator import ManipulatorGui
from holypipette.interface.paramecium_device import ParameciumDeviceSimplifiedInterface

#################################################
# Paramecium experiment with the device method #
#################################################
class ParameciumDeviceGui(ManipulatorGui):

    def __init__(self, stage, microscope, camera, units, config_filename='paramecium_device.cfg'):
        super(ParameciumDeviceGui, self).__init__(camera,
                                            pipette_interface=ParameciumDeviceSimplifiedInterface(stage, microscope, camera, units, config_filename=config_filename))
        self.display_edit_funcs.append(self.display_timer)
        self.setWindowTitle("Paramecium device")
        self.add_config_gui(self.interface.config)

    def register_commands(self):
        # We have all the commands of the pipettes interface
        super(ParameciumDeviceGui, self).register_commands(manipulator_keys = False)

        #self.register_mouse_action(Qt.LeftButton, Qt.ShiftModifier,
        #                           self.interface.move_pipette_floor) # move to floor level, x axis last
        #self.register_mouse_action(Qt.LeftButton, Qt.ControlModifier,
        #                           self.interface.move_pipette_working_level) # move above clicked position

        self.register_key_action(Qt.Key_Space, None,
                                 self.interface.move_pipette_down) # move to impalement level
        self.register_key_action(Qt.Key_0, None,
                                 self.interface.reset_timer)
        self.register_key_action(Qt.Key_Less, None,
                                 self.interface.focus_working_level)
        self.register_key_action(Qt.Key_Greater, None,
                                 self.interface.focus_calibration_level)
        #self.register_key_action(Qt.Key_At, None,
        #                         self.interface.set_center)
        #self.register_key_action(Qt.Key_Home, None,
        #                         self.interface.move_to_center)
        self.register_key_action(Qt.Key_Space, Qt.ControlModifier,
                                 self.interface.move_pipette_in)
        self.register_key_action(Qt.Key_W, None,
                                 self.interface.partial_withdraw)
        self.register_key_action(Qt.Key_Space, Qt.ShiftModifier,
                                 self.interface.move_pipette_until_drop)
        self.register_key_action(Qt.Key_multiply, None,
                                 self.interface.autocenter)

if __name__ == '__main__':
    import sys

    from PyQt5 import QtWidgets

    from holypipette.log_utils import console_logger

    from setup_script import *

    console_logger()  # Log to the standard console as well

    app = QtWidgets.QApplication(sys.argv)
    gui = ParameciumDeviceGui(stage, microscope, camera, units, config_filename='paramecium_device.cfg')
    gui.initialize()
    gui.show()
    ret = app.exec_()

    sys.exit(ret)
