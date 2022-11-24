'''
A display of TIFF files created in a folder.
'''
import sys

from PyQt5 import QtWidgets

from holypipette.log_utils import console_logger
from holypipette.gui import CameraGui

from holypipette.devices.camera.watchdogcamera import WatchdogCamera
import os

path = os.path.expanduser('~/Paramecium data')
camera = WatchdogCamera(path, 1) # pixel per um

console_logger()  # Log to the standard console as well

app = QtWidgets.QApplication(sys.argv)
gui = CameraGui(camera)
gui.initialize()
gui.show()
ret = app.exec_()

sys.exit(ret)
