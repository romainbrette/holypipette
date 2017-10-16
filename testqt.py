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


class TestGui(QtWidgets.QMainWindow):
    calibrate_signal = QtCore.pyqtSignal()

    def __init__(self, camera):
        super(TestGui, self).__init__()
        self.setWindowTitle("Calibration GUI")
        self.camera = camera
        self.video = LiveFeedQt(self.camera,mouse_callback=self.mouse_callback)
        self.setCentralWidget(self.video)
        self.calibration_thread = QtCore.QThread()
        self.calibrator = Calibrator()
        self.calibrator.moveToThread(self.calibration_thread)
        self.calibrate_signal.connect(self.calibrator.do_calibration)
        self.calibration_thread.start()

    def mouse_callback(self, event):
        if event.button() == Qt.LeftButton:
            x, y = event.x(), event.y()
            xs = x - self.video.size().width()/2
            ys = y - self.video.size().height()/2
            # displayed image is not necessarily the same size as the original camera image
            scale = 1.0*self.camera.width / self.video.size().width()
            xs *= scale
            ys *= scale
            print xs, ys
            calibrated_stage.reference_move(calibrated_stage.reference_position() - array([xs, ys, 0]))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_C:
            self.calibrate_signal.emit()
        elif event.key() == Qt.Key_Escape:
            self.close()

    def closeEvent(self, event):
        try:
            self.camera.video.release()  # necessary for OpenCV
        except AttributeError:
            pass
        event.accept()


class Calibrator(QtCore.QObject):

    @QtCore.pyqtSlot()
    def do_calibration(self):
        print('Starting calibration....')
        t1 = time.time()
        calibrated_stage.calibrate()
        t2 = time.time()
        print t2 - t1, 's'
        print('Done')

#camera = OpenCVCamera()
camera = Lumenera()
controller = LuigsNeumann_SM10(stepmoves=False)
stage = ManipulatorUnit(controller, [7, 8])
microscope = Microscope(controller, 9)
calibrated_stage = CalibratedStage(stage, None, microscope, camera=camera)
unit = ManipulatorUnit(controller, [1, 2, 3])
calibrated_unit = CalibratedUnit(unit, calibrated_stage, microscope, camera=camera)
def message(msg):
    print msg

app = QtWidgets.QApplication(sys.argv)
gui = TestGui(camera)
gui.show()
sys.exit(app.exec_())