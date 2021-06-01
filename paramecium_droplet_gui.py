'''
GUI for Paramecium experiments with the droplet method
'''
import sys

import traceback
from PyQt5 import QtWidgets

from holypipette.log_utils import console_logger
from holypipette.interface import AutoPatchInterface
from holypipette.interface.pipettes import PipetteInterface
from holypipette.interface.paramecium import ParameciumInterface
from holypipette.gui import ParameciumDropletGui

from setup_script import *

console_logger()  # Log to the standard console as well

app = QtWidgets.QApplication(sys.argv)
pipette_interface = PipetteInterface(stage, microscope, camera, units)
gui = ParameciumDropletGui(camera, pipette_interface)
gui.initialize()
gui.show()
ret = app.exec_()

sys.exit(ret)
