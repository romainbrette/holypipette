'''
This is a test GUI, to test the functionality.
'''
import inspect
import pickle
import signal
import sys
import traceback
from os.path import expanduser

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt, QPoint

from numpy import array, arange

from devices import *
from gui import *
from vision import *
from autopatch import *
import cv2

import time
from setup_script import *

home = expanduser("~")
config_filename = home+'/config_manipulator.cfg'

# Catch segmentation faults and aborts
def signal_handler(signum, frame):
    print("*** Received signal %d" % signum)
    print("*** Frame: %s" % inspect.getframeinfo(frame))

signal.signal(signal.SIGSEGV, signal_handler)
signal.signal(signal.SIGABRT, signal_handler)

class TestGui(QtWidgets.QMainWindow):
    calibrate_signal = QtCore.pyqtSignal()
    manual_calibrate_signal = QtCore.pyqtSignal()
    recalibrate_signal = QtCore.pyqtSignal()
    auto_recalibrate_signal = QtCore.pyqtSignal()
    motor_ranges_signal = QtCore.pyqtSignal()
    move_signal = QtCore.pyqtSignal()
    patch_signal = QtCore.pyqtSignal()
    photo_signal = QtCore.pyqtSignal()

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
        self.video = LiveFeedQt(self.camera,mouse_callback=self.mouse_callback,image_edit=image_edit)
        self.setCentralWidget(self.video)
        self.calibration_thread = QtCore.QThread()
        self.calibrator = PipetteHandler()
        self.calibrator.moveToThread(self.calibration_thread)
        self.calibrate_signal.connect(self.calibrator.do_calibration)
        self.manual_calibrate_signal.connect(self.calibrator.manual_calibration)
        self.motor_ranges_signal.connect(self.calibrator.do_motor_ranges)
        self.recalibrate_signal.connect(self.calibrator.do_recalibration)
        self.move_signal.connect(self.calibrator.move_pipette)
        self.patch_signal.connect(self.calibrator.do_patch)
        self.photo_signal.connect(self.calibrator.take_photos)
        self.auto_recalibrate_signal.connect(self.calibrator.do_auto_recalibration)
        self.calibration_thread.start()
        self.load()

    def mouse_callback(self, event):
        # Click = move
        # Shift-click = move and patch
        if event.button() == Qt.LeftButton:
            try:
                x, y = event.x(), event.y()
                xs = x - self.video.size().width()/2
                ys = y - self.video.size().height()/2
                # displayed image is not necessarily the same size as the original camera image
                scale = 1.0*self.camera.width / self.video.pixmap().size().width()
                xs *= scale
                ys *= scale
                #calibrated_stage.reference_relative_move(- array([xs, ys, 0]))
                #calibrated_unit.reference_move(array([xs, ys, microscope.position()]))
                self.calibrator.move_position = array([xs, ys, microscope.position()])
                if event.modifiers() == Qt.ShiftModifier:
                    self.patch_signal.emit()
                else:
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
            # Calibration
            elif event.key() == Qt.Key_C:
                if event.modifiers() == Qt.ShiftModifier:
                    self.manual_calibrate_signal.emit()
                    # Manual calibration based on landmark points
                else:
                    self.calibrate_signal.emit()
            # Quit
            elif event.key() == Qt.Key_Escape:
                self.close()
            # Motor ranges
            elif event.key() == Qt.Key_M:
                #self.motor_ranges_signal.emit()
                pass
            # Recalibrate
            elif event.key() == Qt.Key_R:
                if event.modifiers() == Qt.ShiftModifier:
                    self.auto_recalibrate_signal.emit()
                else:
                    self.recalibrate_signal.emit()
            # Save configuration
            elif event.key() == Qt.Key_S:
                self.save()
            # Load configuration
            elif event.key() == Qt.Key_L:
                self.load()
            # Floor Z (coverslip)
            elif event.key() == Qt.Key_F:
                microscope.floor_Z = microscope.position()
                print("Floor Z: "+str(microscope.floor_Z))
            # Zap
            elif event.key() == Qt.Key_Z:
                autopatcher.switch_zap(message)
            # Go to floor Z (coverslip)
            elif event.key() == Qt.Key_G:
                microscope.absolute_move(microscope.floor_Z)
            # Reset camera
            elif event.key() == Qt.Key_F1:
                self.camera.reset()
            # Take photos around current point, assuming tip in focus
            elif event.key() == Qt.Key_P:
                self.photo_signal.emit()
            # Track paramecium
            elif event.key() == Qt.Key_T:
                image_editor.show_paramecium = not image_editor.show_paramecium
                if image_editor.show_paramecium:
                    print('Paramecium tracking is on')
            # Withdraw
            elif event.key() == Qt.Key_W:
                calibrated_unit.withdraw()
            # Landmark point
            elif event.key() == Qt.Key_Asterisk:
                print("Landmark")
                landmark_u.append(calibrated_unit.position())
                landmark_rs.append(calibrated_stage.reference_position())
                # r is the position on screen, and focal plane
                print landmark_r
                position = array([self.camera.width/2, self.camera.height/2, microscope.position()])
                landmark_r.append(position)
            # End position of the axes
            elif event.key() == Qt.Key_E:
                print("End position of axes")
                axes_end.append((calibrated_stage.position(), calibrated_unit.position()))
                if len(axes_end)>=2:
                    position1 = axes_end[-2][0]
                    position2 = axes_end[-1][0]
                    calibrated_stage.min = [min(a,b) for a,b in zip(position1, position2)]
                    calibrated_stage.max = [min(a,b) for a,b in zip(position1, position2)]
                    position1 = axes_end[-2][1]
                    position2 = axes_end[-1][1]
                    calibrated_unit.min = [min(a,b) for a,b in zip(position1, position2)]
                    calibrated_unit.max = [min(a,b) for a,b in zip(position1, position2)]
                    print calibrated_stage.min,calibrated_stage.max,calibrated_unit.min,calibrated_unit.max
        except Exception:
            print(traceback.format_exc())

    def save(self):
        # Saves configuration
        print("Saving configuration")
        cfg = {'stage' : calibrated_stage.save_configuration(),
               'unit' : calibrated_unit.save_configuration(),
               'microscope' : microscope.save_configuration()}
        pickle.dump(cfg, open(config_filename, "wb"))

    def load(self):
        # Loads configuration
        print("Loading configuration")
        cfg = pickle.load(open(config_filename, "rb"))
        microscope.load_configuration(cfg['microscope'])
        calibrated_stage.load_configuration(cfg['stage'])
        calibrated_unit.load_configuration(cfg['unit'])

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


class PipetteHandler(QtCore.QObject): # This could be more general, for each pipette (or maybe for the entire setup)

    @QtCore.pyqtSlot()
    def do_patch(self): # Start the patch-clamp procedure
        try:
            print("Starting patch-clamp")
            autopatcher.run(self.move_position, message)
            print("Done")
        except AutopatchError as e:
            print(str(e))
        except Exception:
            print(traceback.format_exc())

    @QtCore.pyqtSlot()
    def move_pipette(self):
        try:
            calibrated_unit.safe_move(self.move_position)
        except Exception:
            print(traceback.format_exc())

    @QtCore.pyqtSlot()
    def do_calibration(self):
        print('Starting calibration....')
        try:
            t1 = time.time()
            #calibrated_stage.calibrate()
            #calibrated_unit.calibrate_with_stage(message)
            calibrated_unit.calibrate(message)
            t2 = time.time()
            print t2 - t1, 's'
        except Exception:
            print(traceback.format_exc())
        print('Done')

    @QtCore.pyqtSlot()
    def manual_calibration(self):
        print('Manual calibration....')
        try:
            calibrated_unit.manual_calibration((landmark_r[-4:], landmark_u[-4:], landmark_rs[-4:]), message)
        except Exception:
            print(traceback.format_exc())
        print('Done')


    @QtCore.pyqtSlot()
    def do_recalibration(self):
        print('Recalibration')
        calibrated_unit.recalibrate(message)

    @QtCore.pyqtSlot()
    def do_auto_recalibration(self):
        print('Automatic recalibration....')
        try:
            calibrated_unit.auto_recalibrate(message=message)
            print("Done")
        except Exception:
            print(traceback.format_exc())

    @QtCore.pyqtSlot()
    def do_motor_ranges(self):
        print('Measuring motor ranges for the stage')
        calibrated_stage.motor_ranges()
        print stage.min, stage.max
        print('Measuring motor ranges for the unit')
        calibrated_unit.motor_ranges()
        print unit.min, unit.max
        print('Done')

    @QtCore.pyqtSlot()
    def take_photos(self):
        global stack,x0,y0

        print("Taking photos")
        try:
            calibrated_unit.take_photos(message)
        except Exception:
            print(traceback.format_exc())
        print("Done")


class ImageEditor(object): # adds stuff on the image, including paramecium tracker
    def __init__(self):
        self.show_paramecium = False

    def point_paramecium(self, img):
        x,y = where_is_paramecium(img)
        if x is not None:
            cv2.circle(img, (x,y), 50, (0, 0, 255))
        return img

    def edit_image(self, img):
        if self.show_paramecium:
            img = self.point_paramecium(img)
        return img

image_editor = ImageEditor()

def message(msg):
    print msg

def image_edit(img):
    return image_editor.edit_image(img)

amplifier = MultiClampChannel()
pressure = OB1()
autopatcher = AutoPatcher(amplifier, pressure, calibrated_unit)
stack = None
x0, y0 = None, None
landmark_u = [] # Landmark points
landmark_r = []
landmark_rs = []
axes_end = [] # End points of axes

pressure.set_pressure(25)

app = QtWidgets.QApplication(sys.argv)
gui = TestGui(camera)
gui.show()
ret = app.exec_()

sys.exit(ret)
