'''
This GUI only shows the camera image, without any additional controls (stage,
manipulators, pressure controller, etc.)
'''
import sys
from os.path import expanduser

from PyQt5 import QtWidgets

from gui.camera import CameraGui

home = expanduser("~")
config_filename = home+'/config_manipulator.cfg'

from setup_script import *

app = QtWidgets.QApplication(sys.argv)
gui = CameraGui(camera)
gui.show()
ret = app.exec_()

sys.exit(ret)
