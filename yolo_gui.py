'''
This GUI only shows the camera image, without any additional controls (stage,
manipulators, pressure controller, etc.)
'''
import sys

from PyQt5 import QtWidgets

from holypipette.interface import YoloTracker
from holypipette.gui import TrackerGui
from holypipette.log_utils import console_logger

from setup_script import *

console_logger()  # Log to the standard console as well

yolo_tracker = YoloTracker(yolo_path='/home/marcel/programming/Paramecium-deeplearning/yolov5') 


app = QtWidgets.QApplication(sys.argv)
gui = TrackerGui(camera, yolo_tracker)
gui.initialize()
gui.show()
ret = app.exec_()

sys.exit(ret)
