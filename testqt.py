'''
This is a test GUI, to test the functionality.
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
        t1 = time.time()
        calibrated_stage.calibrate(message)
        t2 = time.time()
        print t2 - t1, 's'
        print('Done')

controller = LuigsNeumann_SM10(stepmoves=False)
stage = ManipulatorUnit(controller,[7,8])
microscope = Microscope(controller,9)
calibrated_stage = CalibratedStage(stage, None, microscope, camera=camera)
unit = ManipulatorUnit(controller, [1,2,3])
calibrated_unit = CalibratedUnit(unit, calibrated_stage, microscope, camera=camera)
def message(msg):
    print msg

app = QtWidgets.QApplication(sys.argv)
gui = TestGui()
sys.exit(app.exec_())