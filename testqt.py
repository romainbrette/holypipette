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
    calibrate_signal = QtCore.pyqtSignal()
    recalibrate_signal = QtCore.pyqtSignal()
    motor_ranges_signal = QtCore.pyqtSignal()
    move_signal = QtCore.pyqtSignal()
    patch_signal = QtCore.pyqtSignal()

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
        self.calibrate_signal.connect(self.calibrator.do_calibration)
        self.motor_ranges_signal.connect(self.calibrator.do_motor_ranges)
        self.recalibrate_signal.connect(self.calibrator.do_recalibration)
        self.move_signal.connect(self.calibrator.move_pipette)
        self.patch_signal.connect(self.calibrator.do_patch)
        self.calibration_thread.start()

    def mouse_callback(self, event):
        # Click = move
        # Shift-click = move and patch
        if event.button() == Qt.LeftButton:
            try:
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
            # Patch
            elif event.key() == Qt.Key_P:
                self.patch_signal.emit()
            # Calibration
            elif event.key() == Qt.Key_C:
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
        except Exception:
            print(traceback.format_exc())

    def save(self):
        # Saves configuration
        print("Saving configuration")
        cfg = {'stage.M' : calibrated_stage.M,
               'stage.r0' : calibrated_stage.r0,
               'unit.M' : calibrated_unit.M,
               'unit.r0' : calibrated_unit.r0,
               'microscope.up' : microscope.up_direction,
               'unit.up' : calibrated_unit.up_direction}
        pickle.dump(cfg, open(config_filename, "wb"))

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
    def do_patch(self): # Start the patch-clamp procedure
        print("Starting patch-clamp")
        patcher.start()
        # Pressure level 1
        pressure.set_pressure(param_pressure_near)

        # Wait for a few seconds
        time.sleep(4.)

        # Check initial resistance
        R = patcher.resistance()
        print("Resistance:" + str(R))
        if R<param_Rmin:
            print("Resistance is too low (broken tip?)")
            patcher.stop()
            return
        elif R>param_Rmax:
            print("Resistance is too high (obstructed?)")
            patcher.stop()
            return

        # Move pipette to target
        calibrated_unit.safe_move(self.move_position + microscope.up_direction*array([0,0,1.])*param_cell_distance)

        # Check resistance again
        oldR = R
        R = patcher.resistance()
        if abs(R - oldR) > param_max_R_increase:
            print("Pipette is obstructed; R = "+str(R))
            patcher.stop()
            return

        # Release pressure
        print("Releasing pressure")
        pressure.set_pressure(0)

        # Pipette offset
        amplifier.auto_pipette_offset()
        time.sleep(2) # why?

        # Approach and make the seal
        print("Approaching the cell")
        success = False
        for _ in range(param_max_distance): # move 15 um down
            # move by 1 um down
            # Cleaner: use reference relative move
            unit.relative_move(1, axis=2) #*calibrated_unit.up_position[2]
            unit.wait_until_still(2)
            time.sleep(1)
            oldR = R
            R = patcher.resistance()
            print("R = "+str(patcher.resistance()))
            if R>oldR*(1+param_cell_R_increase): # R increases: near cell?
                time.sleep(10)
                if R>oldR*(1+param_cell_R_increase):
                    # Still higher, we are near the cell
                    print("Sealing, R = "+str(patcher.resistance()))
                    pressure.set_pressure(param_pressure_sealing)
                    t0 = time.time()
                    t = t0
                    R = patcher.resistance()
                    while (R<param_gigaseal_R) | (t-t0<param_seal_min_time):
                        # Wait at least 15s and until we get a Gigaseal
                        t = time.time()
                        if t-t0<param_Vramp_duration:
                            # Ramp to -70 mV in 10 s (default)
                            amplifier.set_holding(param_Vramp_amplitude*(t-t0)/param_Vramp_duration)
                        if t-t0>=param_seal_deadline:
                            # No seal in 90 s
                            print("Seal unsuccessful")
                            patcher.stop()
                            return
                        R = patcher.resistance()
                    success = True
                    break
        pressure.set_pressure(0)
        if not success:
            print("Seal unsuccessful")
            patcher.stop()
            return

        print("Seal successful, R = "+str(patcher.resistance()))

        # Go whole-cell
        print("Breaking in")
        trials = 0
        R = patcher.resistance()
        if R<param_gigaseal_R:
            print("Seal lost")
            patcher.stop()
            return

        while patcher.resistance()>param_max_cell_R: # Success when resistance goes below 300 MOhm
            if trials==param_breakin_trials:
                print("Break-in unsuccessful")
                patcher.stop()
                return
            if param_zap:
                amplifier.zap()
            pressure.ramp(amplitude=param_pressure_ramp_amplitude, duration=param_pressure_ramp_duration)
            time.sleep(1.3)
            trials+=1

        print("Successful break-in, R = "+str(patcher.resistance()))

        patcher.stop()
        print("Done")

    @QtCore.pyqtSlot()
    def move_pipette(self):
        calibrated_unit.safe_move(self.move_position)

    @QtCore.pyqtSlot()
    def do_calibration(self):
        print('Starting calibration....')
        t1 = time.time()
        try:
            calibrated_unit.calibrate(message)
            #calibrated_stage.calibrate()
        except Exception:
            print(traceback.format_exc())
        t2 = time.time()
        print t2 - t1, 's'
        print('Done')

    @QtCore.pyqtSlot()
    def do_recalibration(self):
        print('Starting recalibration....')
        calibrated_unit.recalibrate(message)
        print('Done')

    @QtCore.pyqtSlot()
    def do_motor_ranges(self):
        print('Measuring motor ranges for the stage')
        calibrated_stage.motor_ranges()
        print stage.min, stage.max
        print('Measuring motor ranges for the unit')
        calibrated_unit.motor_ranges()
        print unit.min, unit.max
        print('Done')


#u0 = unit.position()
#u0_stage = stage.position()
#z0 = microscope.position()

def message(msg):
    print msg

amplifier = MultiClampChannel()
patcher = MulticlampPatcher(amplifier)
pressure = OB1()

app = QtWidgets.QApplication(sys.argv)
gui = TestGui(camera)
gui.show()
ret = app.exec_()

#unit.absolute_move(u0)
#stage.absolute_move(u0_stage)
#microscope.absolute_move(z0)
sys.exit(ret)
