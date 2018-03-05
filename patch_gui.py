import sys

from PyQt5 import QtWidgets

from holypipette.base.executor import console_logger
from holypipette.controller import AutoPatchController
from holypipette.controller.pipettes import PipetteController
from holypipette.gui import PatchGui

from setup_script import *

console_logger()  # Log to the standard console as well

app = QtWidgets.QApplication(sys.argv)

pipette_controller = PipetteController(stage, microscope, camera, units)
amplifier = None
pressure = None
patch_controller = AutoPatchController(amplifier, pressure, pipette_controller)
gui = PatchGui(camera, pipette_controller, patch_controller)
gui.initialize()
gui.show()
ret = app.exec_()

sys.exit(ret)
