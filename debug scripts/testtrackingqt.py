'''
This is a test GUI, to test the functionality.
'''
from holypipette.devices import *
from holypipette.vision import *
from holypipette.gui import *
import sys
import cv2
import time
from numpy import array
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from math import atan2

# This is a setup script that is specific of the rig
from setup_script import *

def moveto(x, y):
    xs = x-camera.width/2
    ys = y-camera.height/2
    #print xs, ys
    calibrated_stage.reference_move(calibrated_stage.reference_position()-array([xs, ys, 0]))

def where_is_paramecium(frame): # Locate paramecium
    height, width = frame.shape[:2]
    ratio = width/256
    resized = cv2.resize(frame, (width/ratio, height/ratio))
    gauss = cv2.GaussianBlur(resized, (9, 9), 0)
    canny = cv2.Canny(gauss, gauss.shape[0]/8, gauss.shape[0]/8)
    ret, thresh = cv2.threshold(canny, 127, 255, 0)
    ret = cv2.findContours(thresh, 1, 2)
    contours, hierarchy = ret[-2], ret[-1] # for compatibility with opencv2 and 3
    distmin = 1e6
    for cnt in contours:
        try:
            M = cv2.moments(cnt)
            if (cv2.arcLength(cnt, True) > 90) & bool(M['m00']):
                (x, y), radius = cv2.minEnclosingCircle(cnt)
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])
                u20 = int(M['m20']/M['m00'] - cx**2)
                u02 = int(M['m02'] / M['m00'] - cy ** 2)
                u11 = int(M['m11'] / M['m00'] - cx * cy)
                theta = atan2((u20-u02), 2*u11)/2
                radius = int(radius)
                dist = ((x - width/2) ** 2 + (y - height/2) ** 2) ** 0.5
                if (radius < 55) & (radius > 25) & (dist<distmin):
                    distmin=dist
                    xmin, ymin =x, y
                    angle = theta # not used here
        except cv2.error:
            pass
    if distmin<1e5:
        return xmin*ratio,ymin*ratio
    else:
        return None,None


class TestGui(QtWidgets.QMainWindow):
    calibrate_signal = QtCore.pyqtSignal()
    tracking_signal = QtCore.pyqtSignal()

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

        self.tracking_thread = QtCore.QThread()
        self.tracker = Tracker()
        self.tracker.moveToThread(self.tracking_thread)
        self.tracking_signal.connect(self.tracker.do_tracking)
        self.tracking_thread.start()


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
        elif event.key() == Qt.Key_T:
            self.tracking_signal.emit()
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
        calibrated_stage.calibrate(message)
        t2 = time.time()
        print t2 - t1, 's'
        print('Done')

class Tracker(QtCore.QObject):

    @QtCore.pyqtSlot()
    def do_tracking(self):
        while True:
            frame = camera.snap()
            x,y = where_is_paramecium(frame)
            print x,y
            if x is not None:
                #moveto(x,y)
                pass

def message(msg):
    print msg

app = QtWidgets.QApplication(sys.argv)
gui = TestGui(camera)
gui.show()
sys.exit(app.exec_())
