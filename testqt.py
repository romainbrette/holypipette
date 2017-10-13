'''
This is a test GUI, to test the functionality.

Seems to work, except the camera apparently doesn't start until waitkey (??)
'''
from devices import *
from vision import *
from gui import *
import sys
import cv2
import time
from numpy import array
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt


class TestGui(QtCore.QObject):
    calibrate_signal = QtCore.pyqtSignal()

    def __init__(self):
        super(TestGui, self).__init__()
        self.camera = OpenCVCamera()
        # camera = Lumenera()
        self.video = LiveFeedQt(self.camera, key_callback=self.keypress_callback,
                                mouse_callback=self.mouse_callback)
        self.calibration_thread = QtCore.QThread()
        self.calibrator = Calibrator()
        self.calibrator.moveToThread(self.calibration_thread)
        self.calibrate_signal.connect(self.calibrator.do_calibration)
        self.calibration_thread.start()
        self.video.show()

    def mouse_callback(self, event):
        if event.button() == Qt.LeftButton:
            x, y = event.x(), event.y()
            xs = x - self.camera.width/2
            ys = y - self.camera.height/2
            print xs, ys

    def keypress_callback(self, event):
        if event.key() == Qt.Key_C:
            self.calibrate_signal.emit()


class Calibrator(QtCore.QObject):

    @QtCore.pyqtSlot()
    def do_calibration(self):
        print('Starting calibration....')
        time.sleep(1)
        print('Still doing something....')
        time.sleep(1)
        print('Done')

app = QtWidgets.QApplication(sys.argv)
gui = TestGui()
sys.exit(app.exec_())