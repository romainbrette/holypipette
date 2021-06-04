'''
GUI for Paramecium experiments with the device method
'''
import sys

from PyQt5 import QtWidgets

from holypipette.log_utils import console_logger
from holypipette.interface.pipettes import PipetteInterface
from holypipette.interface.paramecium_device import ParameciumDeviceInterface
from holypipette.gui import ParameciumDeviceGui

from setup_script import *

console_logger()  # Log to the standard console as well

app = QtWidgets.QApplication(sys.argv)
pipette_interface = PipetteInterface(stage, microscope, camera, units, config_filename='paramecium_device.cfg')
gui = ParameciumDeviceGui(camera, pipette_interface)
gui.initialize()
gui.show()
ret = app.exec_()

sys.exit(ret)
