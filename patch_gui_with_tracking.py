import sys
import traceback

from PyQt5 import QtWidgets

from holypipette.log_utils import console_logger
from holypipette.interface import AutoPatchInterface
from holypipette.interface.pipettes import PipetteInterface
from holypipette.gui import TrackingPatchGui
from holypipette.devices import *

from setup_script import *

amplifier, pressure = None, None
try:
    amplifier = MultiClampChannel()
except Exception:
    print(traceback.format_exc())

try:
    pressure = OB1()
    pressure.set_pressure(25)
except Exception:
    print(traceback.format_exc())

console_logger()  # Log to the standard console as well

app = QtWidgets.QApplication(sys.argv)

pipette_controller = PipetteInterface(stage, microscope, camera, units)
patch_controller = AutoPatchInterface(amplifier, pressure, pipette_controller)
gui = TrackingPatchGui(camera, pipette_controller, patch_controller)
gui.initialize()
gui.show()
ret = app.exec_()
sys.exit(ret)
