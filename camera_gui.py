'''
This GUI only shows the camera image, without any additional controls (stage,
manipulators, pressure controller, etc.)
'''
import sys

from PyQt5 import QtWidgets

from holypipette.log_utils import console_logger
from holypipette.gui import CameraGui

from setup_script import *

console_logger()  # Log to the standard console as well

app = QtWidgets.QApplication(sys.argv)
gui = CameraGui(camera)
gui.initialize()
gui.show()
ret = app.exec_()

sys.exit(ret)
