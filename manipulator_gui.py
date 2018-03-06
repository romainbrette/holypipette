import sys

from PyQt5 import QtWidgets

from holypipette.log_utils import console_logger
from holypipette.controller.pipettes import PipetteController
from holypipette.gui.manipulator import ManipulatorGui

from setup_script import *

console_logger()  # Log to the standard console as well

app = QtWidgets.QApplication(sys.argv)

controller = PipetteController(stage, microscope, camera, units)
gui = ManipulatorGui(camera, controller)
gui.initialize()
gui.show()
ret = app.exec_()

sys.exit(ret)
