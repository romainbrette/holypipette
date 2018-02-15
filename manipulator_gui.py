import sys

from PyQt5 import QtWidgets

from controller.pipettes import PipetteController
from gui.manipulator import ManipulatorGui

from setup_script import *

app = QtWidgets.QApplication(sys.argv)

controller = PipetteController(stage, microscope, camera, units)
gui = ManipulatorGui(camera, controller)
app.installEventFilter(gui)
gui.show()
ret = app.exec_()

sys.exit(ret)
