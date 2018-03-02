import sys

from PyQt5 import QtWidgets

from controller import AutoPatchController
from controller.pipettes import PipetteController
from gui.patch import PatchGui

from setup_script import *

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
