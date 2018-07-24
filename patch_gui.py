import sys

import traceback
from PyQt5 import QtWidgets

from holypipette.log_utils import console_logger
from holypipette.interface import AutoPatchInterface
from holypipette.interface.pipettes import PipetteInterface
from holypipette.gui import PatchGui

from setup_script import *

console_logger()  # Log to the standard console as well

app = QtWidgets.QApplication(sys.argv)

pipette_controller = PipetteInterface(stage, microscope, camera, units)
patch_controller = AutoPatchInterface(amplifier, pressure, pipette_controller)
gui = PatchGui(camera, pipette_controller, patch_controller)
gui.initialize()
gui.show()
ret = app.exec_()

sys.exit(ret)
