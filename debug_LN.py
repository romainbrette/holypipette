'''
A program to debug the L&N SM10.
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
import traceback
import pickle
from numpy.linalg import pinv
import inspect
import signal

# This is a setup script that is specific of the rig
from setup_script import *
from os.path import expanduser

from parameters import *

home = expanduser("~")
config_filename = home+'/config_manipulator.cfg'

# Catch segmentation faults and aborts
def signal_handler(signum, frame):
    print("*** Received signal %d" % signum)
    print("*** Frame: %s" % inspect.getframeinfo(frame))

signal.signal(signal.SIGSEGV, signal_handler)
signal.signal(signal.SIGABRT, signal_handler)

class TestGui(QtWidgets.QMainWindow):
    debug_signal = QtCore.pyqtSignal()
    move_signal = QtCore.pyqtSignal()
    recalibrate_signal = QtCore.pyqtSignal()

    def __init__(self, camera):
        super(TestGui, self).__init__()
        self.setWindowTitle("Calibration GUI")
        self.status_bar = QtWidgets.QStatusBar()
        self.status_label = QtWidgets.QLabel()
        self.status_bar.addPermanentWidget(self.status_label)
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)
        self.camera = camera
        self.update_status_bar()
        self.video = LiveFeedQt(self.camera,mouse_callback=self.mouse_callback)
        self.setCentralWidget(self.video)
        self.calibration_thread = QtCore.QThread()
        self.calibrator = Calibrator()
        self.calibrator.moveToThread(self.calibration_thread)
        self.debug_signal.connect(self.calibrator.do_debug)
        self.move_signal.connect(self.calibrator.move_pipette)
        self.recalibrate_signal.connect(self.calibrator.do_recalibration)
        self.calibration_thread.start()
        self.load()

    def mouse_callback(self, event):
        # Click = move
        # Shift-click = move and patch
        if event.button() == Qt.LeftButton:
            try:
                print("moving")
                x, y = event.x(), event.y()
                xs = x - self.video.size().width()/2
                ys = y - self.video.size().height()/2
                # displayed image is not necessarily the same size as the original camera image
                scale = 1.0*self.camera.width / self.video.size().width()
                xs *= scale
                ys *= scale
                #calibrated_stage.reference_relative_move(- array([xs, ys, 0]))
                #calibrated_unit.reference_move(array([xs, ys, microscope.position()]))
                self.calibrator.move_position = array([xs, ys, microscope.position()])
                self.move_signal.emit()
            except Exception:
                print(traceback.format_exc())

    def keyPressEvent(self, event):
        try:
            # Arrows move the stage
            if event.modifiers() == Qt.ShiftModifier:
                distance = 50
            elif event.modifiers() == Qt.AltModifier:
                distance = 2.5
            else:
                distance = 10
            if event.key() == Qt.Key_Left:
                stage.relative_move(-distance,0)
            elif event.key() == Qt.Key_Right:
                stage.relative_move(distance, 0)
            elif event.key() == Qt.Key_Up:
                stage.relative_move(-distance, 1)
            elif event.key() == Qt.Key_Down:
                stage.relative_move(distance, 1)
            elif event.key() == Qt.Key_PageUp:
                microscope.relative_move(distance)
            elif event.key() == Qt.Key_PageDown:
                microscope.relative_move(-distance)
            # Changing camera exposure
            elif event.key() == Qt.Key_Plus:
                self.camera.change_exposure(2.5)
                self.update_status_bar()
            elif event.key() == Qt.Key_Minus:
                self.camera.change_exposure(-2.5)
                self.update_status_bar()
            # Recalibrate
            elif event.key() == Qt.Key_R:
                self.recalibrate_signal.emit()
            # Calibration
            elif event.key() == Qt.Key_D:
                self.debug_signal.emit()
            # Quit
            elif event.key() == Qt.Key_Escape:
                self.close()
        except Exception:
            print(traceback.format_exc())

    def load(self):
        # Loads configuration
        print("Loading configuration")
        cfg = pickle.load(open(config_filename, "rb"))
        calibrated_stage.M = cfg['stage.M']
        calibrated_stage.Minv = pinv(calibrated_stage.M)
        calibrated_stage.r0 = cfg['stage.r0']
        calibrated_stage.calibrated = True

        calibrated_unit.M = cfg['unit.M']
        calibrated_unit.Minv = pinv(calibrated_unit.M)
        calibrated_unit.r0 = cfg['unit.r0']
        calibrated_unit.calibrated = True
        calibrated_unit.up_direction = cfg['unit.up']

        microscope.up_direction = cfg['microscope.up']

    def update_status_bar(self):
        exposure = self.camera.get_exposure()
        if exposure > 0:
            self.status_label.setText("Exposure time: %.2fms" % exposure)

    def closeEvent(self, event):
        try:
            self.camera.video.release()  # necessary for OpenCV
        except AttributeError:
            pass
        event.accept()


class Calibrator(QtCore.QObject):

    @QtCore.pyqtSlot()
    def do_debug(self): # Debug the controller
        print("Debugging")
        try:
            image = crop_center(camera.snap())
            cv2.imwrite('./screenshots/firstimage.jpg', image)
            microscope.relative_move(2)
            microscope.wait_until_still()
            img = crop_center(camera.snap())
            _,_,c1 = templatematching(image,img)
            microscope.relative_move(-4)
            microscope.wait_until_still()
            img = crop_center(camera.snap())
            _, _, c2 = templatematching(image, img)
            threshold = min((c1,c2))
            print("Threshold="+str(threshold))

            microscope.relative_move(2)
            microscope.wait_until_still()

            fast = False

            failure = False
            for axis in [1,2,3,7,8,9]:
                print("Moving along axis "+str(axis))
                for x in [4,8,16,32,64,128]:
                    print(x)
                    controller.relative_move(-x, axis=axis, fast=fast)
                    controller.wait_until_still([axis])
                    controller.relative_move(-x, axis=axis, fast=fast)
                    controller.wait_until_still([axis])
                    controller.relative_move(2*x, axis=axis, fast=fast)
                    controller.wait_until_still([axis])
                    time.sleep(2)
                    img = crop_center(camera.snap())
                    _, _, c = templatematching(image, img)
                    print("Correlation = "+str(c))
                    if c<threshold:
                        print("Failed!")
                        failure = True
                        cv2.imwrite('./screenshots/failimage.jpg', img)
                        break
                if failure:
                    break
        except Exception:
            print(traceback.format_exc())

    @QtCore.pyqtSlot()
    def move_pipette(self):
        calibrated_unit.safe_move(self.move_position)

    @QtCore.pyqtSlot()
    def do_recalibration(self):
        print('Starting recalibration....')
        calibrated_unit.recalibrate(message)
        print('Done')


def message(msg):
    print msg

amplifier = MultiClampChannel()
patcher = MulticlampPatcher(amplifier)
pressure = OB1()

app = QtWidgets.QApplication(sys.argv)
gui = TestGui(camera)
gui.show()
ret = app.exec_()

sys.exit(ret)
