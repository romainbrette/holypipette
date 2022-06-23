'''
A GUI for automated camera snapshots with stage movements
'''
import sys

from PyQt5 import QtWidgets

from holypipette.log_utils import console_logger
from holypipette.interface.stage import StageInterface
from holypipette.gui.automated_microscope import AutomatedMicroscopeGui

from setup_script import *

console_logger()  # Log to the standard console as well

app = QtWidgets.QApplication(sys.argv)

controller = StageInterface(stage, microscope, camera)
gui = AutomatedMicroscopeGui(camera, controller)
gui.initialize()
gui.show()
ret = app.exec_()

sys.exit(ret)
