'''
This is a test GUI, to test the functionality.
'''
import inspect
import pickle
import signal
import sys
import traceback
import collections
from os.path import expanduser

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt, QPoint

from numpy import array, arange, mean, cos, sin, mgrid, sum, zeros, var

from autopatch.parameters import *
from devices import *
from gui import *
from vision import *
from autopatch import *
import cv2
import numpy as np

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
    pipette_back_signal = QtCore.pyqtSignal()
    stage_calibrate_signal = QtCore.pyqtSignal()
    manual_calibrate_signal = QtCore.pyqtSignal()
    recalibrate_signal = QtCore.pyqtSignal()
    auto_recalibrate_signal = QtCore.pyqtSignal()
    motor_ranges_signal = QtCore.pyqtSignal()
    move_signal = QtCore.pyqtSignal()
    patch_signal = QtCore.pyqtSignal()
    patch_nomove_signal = QtCore.pyqtSignal()
    break_signal = QtCore.pyqtSignal()
    photo_signal = QtCore.pyqtSignal()
    objective_signal = QtCore.pyqtSignal()
    paramecium_signal = QtCore.pyqtSignal()
    catch_signal = QtCore.pyqtSignal()
    ##### HOANG
    pipette_cleaning_signal = QtCore.pyqtSignal()
    initial_location_signal = QtCore.pyqtSignal()
    #movement_compensation_signal = QtCore.pyqtSignal()
    move_patch_clean_signal = QtCore.pyqtSignal()
    nomove_patch_clean_signal = QtCore.pyqtSignal()
    tracking_signal = QtCore.pyqtSignal()
    testing_calibrate_signal = QtCore.pyqtSignal()
    testing_photo_signal = QtCore.pyqtSignal()
    cardinal_positions_signal = QtCore.pyqtSignal()

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
        self.video = LiveFeedQt(self.camera,mouse_callback=self.mouse_callback,image_edit=image_edit, display_edit=display_edit)
        self.setCentralWidget(self.video)
        self.calibration_thread = QtCore.QThread()
        self.calibrator = PipetteHandler()
        self.calibrator.moveToThread(self.calibration_thread)
        self.calibrate_signal.connect(self.calibrator.do_calibration)
        self.stage_calibrate_signal.connect(self.calibrator.stage_calibrate)
        self.manual_calibrate_signal.connect(self.calibrator.manual_calibration)
        self.motor_ranges_signal.connect(self.calibrator.do_motor_ranges)
        self.recalibrate_signal.connect(self.calibrator.do_recalibration)
        self.pipette_back_signal.connect(self.calibrator.pipette_back)
        self.move_signal.connect(self.calibrator.move_pipette)
        self.patch_signal.connect(self.calibrator.do_patch)
        self.patch_nomove_signal.connect(self.calibrator.patch_without_move)
        self.break_signal.connect(self.calibrator.break_in)
        self.photo_signal.connect(self.calibrator.take_photos)
        self.objective_signal.connect(self.calibrator.change_objective)
        self.paramecium_signal.connect(self.calibrator.pick_paramecium)
        self.auto_recalibrate_signal.connect(self.calibrator.do_auto_recalibration)
        self.catch_signal.connect(self.calibrator.catch_paramecium)
        self.calibration_thread.start()
        self.load()
        ##### HOANG
        self.pipette_cleaning_signal.connect(self.calibrator.do_cleaning_pipette)
        self.initial_location_signal.connect(self.calibrator.do_initial_location)
        #self.movement_compensation_signal.connect(self.calibrator.do_movement_compensate)
        self.move_patch_clean_signal.connect(self.calibrator.do_move_patch_clean)
        self.nomove_patch_clean_signal.connect(self.calibrator.do_nomove_patch_clean)
        # self.tracking_thread = QtCore.QThread()
        # self.tracker = Tracker()
        # self.tracker.moveToThread(self.tracking_thread)
        # self.tracking_signal.connect(self.tracker.do_tracking)
        # self.tracking_thread.start()
        # self.multitracker = cv2.MultiTracker_create()
        self.testing_calibrate_signal.connect(self.calibrator.do_testing_calibration)
        self.testing_photo_signal.connect(self.calibrator.take_testing_photos)
        self.cardinal_positions_signal.connect(self.calibrator.test_cardinal_positions)

    def mouse_callback(self, event):
        # Click = move
        # Shift-click = move and patch
        global moveList
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
                elif event.modifiers() == Qt.ControlModifier:
                    self.patch_nomove_signal.emit()
                else:
                    self.move_signal.emit()
            except Exception:
                print(traceback.format_exc())
        ##### HOANG
        # Integrated patching and cleaning (1 neuron)
        if event.button() == Qt.RightButton:
            try:
                x, y = event.x(), event.y()
                xs = x - self.video.size().width() / 2
                ys = y - self.video.size().height() / 2
                scale = 1.0 * self.camera.width / self.video.pixmap().size().width()
                xs *= scale
                ys *= scale
                moveList.append(array([xs, ys, microscope.position()]))
            except Exception:
                print(traceback.format_exc())

    def keyPressEvent(self, event):
        global calibrated_unit

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
            # Select first manipulator
            elif event.key() == Qt.Key_1:
                print('First manipulator selected') # status bar?
                calibrated_unit = calibrated_units[0]
            # Select second manipulator
            elif event.key() == Qt.Key_2:
                print('Second manipulator selected') # status bar?
                calibrated_unit = calibrated_units[1]
            # Calibration
            elif event.key() == Qt.Key_C:
                if event.modifiers() == Qt.ShiftModifier:
                    self.manual_calibrate_signal.emit()
                    # Manual calibration based on landmark points
                elif event.modifiers() == Qt.ControlModifier:
                    self.stage_calibrate_signal.emit()
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
                calibrated_unit.analyze_calibration()
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
            # Impale paramecium
            elif event.key() == Qt.Key_Return:
                self.paramecium_signal.emit()
            # Catch paramecium
            elif event.key() == Qt.Key_Q:
                self.catch_signal.emit()
            # Drop paramecium
            elif event.key() == Qt.Key_D:
                pressure.set_pressure(100) # should be in thread
                time.sleep(1)
                calibrated_unit.relative_move(2000 * calibrated_unit.up_direction[0], 0)
                calibrated_unit.wait_until_still()
                pressure.set_pressure(0)
            # Withdraw
            elif event.key() == Qt.Key_W:
                calibrated_unit.withdraw()
            # Move pipette back after a change
            elif event.key() == Qt.Key_B:
                self.pipette_back_signal.emit()
            # Change objective
            elif event.key() == Qt.Key_O:
                self.objective_signal.emit()
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
                    calibrated_stage.max = [max(a,b) for a,b in zip(position1, position2)]
                    position1 = axes_end[-2][1]
                    position2 = axes_end[-1][1]
                    calibrated_unit.min = [min(a,b) for a,b in zip(position1, position2)]
                    calibrated_unit.max = [max(a,b) for a,b in zip(position1, position2)]
                    print calibrated_stage.min,calibrated_stage.max,calibrated_unit.min,calibrated_unit.max
            # Image analysis
            elif event.key() == Qt.Key_A:
                print("Taking photos for subsequent image analysis")
                # Stack of photos, full field
                # Move a little bit
                for k in range(10):
                    print("Stack {}".format(k))
                    z = microscope.position() + arange(-stack_depth,stack_depth+1)
                    microscope.stack(camera, z, save = 'stack{}.'.format(k))
                    calibrated_stage.relative_move(10, axis = 0)
                    calibrated_stage.wait_until_still(0)
                print("Done")
            ##### HOANG
            #z and us: not necessary
            #Bath location to be involved in the calibration later (Ex, after the current calibration).
            #Store the position of the washing bath
            elif event.key() == Qt.Key_F3:
                global u4
                u4 = calibrated_unit.position()
                print("Washing bath location: Done. Locate the rinsing bath and press F4")
            #Store the position of the rinsing bath
            elif event.key() == Qt.Key_F4:
                if amplifier is None:
                    print("Amplifier not available. Aborting.")
                    return
                else:
                    global u5
                    u5 = calibrated_unit.position()
                    print("Bath location process: Done. Ready for pipette cleaning!")

            # elif event.key() == Qt.Key_F2:
            #     global z3, u3
            #     z3 = microscope.position()
            #     u3 = calibrated_unit.position()
            #     self.pipette_cleaning_signal.emit()

            elif event.key() == Qt.Key_H:
                global z3,u3,moveList
                z3 = microscope.position()
                u3 = calibrated_unit.position()
                self.move_patch_clean_signal.emit()

            elif event.key() == Qt.Key_Y:
                global z3, u3
                z3 = microscope.position()
                u3 = calibrated_unit.position()
                self.nomove_patch_clean_signal.emit()

            elif event.key() == Qt.Key_N:
                global z6,u6,us6
                z6 = microscope.position()
                u6 = calibrated_unit.position()
                us6 = stage.position()

            elif event.key() == Qt.Key_I:
                self.initial_location_signal.emit()

            # elif event.key() == Qt.Key_U:
            #     global boxes
            #     self.tracking_signal.emit()

            elif event.key() == Qt.Key_F5:
                self.testing_calibrate_signal.emit()

            elif event.key() == Qt.Key_F6:
                self.testing_photo_signal.emit()

            elif event.key() == Qt.Key_F7:
                self.cardinal_positions_signal.emit()

        except Exception:
            print(traceback.format_exc())

    def save(self):
        # Saves configuration
        print("Saving configuration")
        cfg = {'stage' : calibrated_stage.save_configuration(),
               'units' : [U.save_configuration() for U in calibrated_units],
               'microscope' : microscope.save_configuration()}
        pickle.dump(cfg, open(config_filename, "wb"))

    def load(self):
        # Loads configuration
        print("Loading configuration")
        try:
            cfg = pickle.load(open(config_filename, "rb"))
            microscope.load_configuration(cfg['microscope'])
            calibrated_stage.load_configuration(cfg['stage'])
            cfg_units = cfg['units']
            for i,cfg_unit in enumerate(cfg_units):
                calibrated_units[i].load_configuration(cfg_unit)
            #calibrated_units[0].load_configuration(cfg['unit'])
            calibrated_unit.analyze_calibration()
        except Exception:
            print("Configuration file could not be loaded.")

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
    def catch_paramecium(self):
        # Catch a paramecium by aspiration
        try:
            print("Catching paramecium")
            pressure.set_pressure(25)
            image_editor.show_paramecium = True

            while 1:
                if paramecium_x is not None:
                    xs,ys = paramecium_x-camera.width/2, paramecium_y-camera.height/2
                    pixel_per_um = calibrated_stage.pixel_per_um()[0]
                    maxd = 300*pixel_per_um # um
                    if (xs**2 + ys**2)<maxd**2:
                        print("Paramecium!")
                        pressure.set_pressure(10)
                        time.sleep(0.5)
                        calibrated_unit.relative_move(2000*calibrated_unit.up_direction[2],2)
                        calibrated_unit.wait_until_still()
                        pressure.set_pressure(0)
                        break

            print("Done")
        except Exception:
            print(traceback.format_exc())

    @QtCore.pyqtSlot()
    def pick_paramecium(self): # Wait for Paramecium to stop, then move pipette and penetrate
        try:
            print("Starting automatic Paramecium impalement")
            # First wait for Paramecium to stop
            image_editor.show_paramecium = True
            position_history = collections.deque(maxlen=30)
            while 1:
                # Calculate variance of position
                if len(position_history) == position_history.maxlen:
                    xpos, ypos = zip(*position_history)
                    movement = (var(xpos) + var(ypos)) ** .5
                    if movement < 1:  # 1 pixel
                        print("Paramecium has stopped!")
                        break

                time.sleep(0.1)
                if paramecium_x is not None:
                    position_history.append((paramecium_x, paramecium_y))

            print("Moving the pipette on the cell")
            xs,ys = paramecium_x-camera.width/2, paramecium_y-camera.height/2
            #xs,ys=0,0
            calibrated_unit.reference_move(array([xs, ys, microscope.position() + microscope.up_direction * 50]))
            calibrated_unit.wait_until_still()

            print("Moving the pipette down")
            x = xs+camera.width/2
            y = ys+camera.height/2
            pixel_per_um = calibrated_stage.pixel_per_um()[0]
            size = int(30 / pixel_per_um)  # 30 um around tip

            for i in range(20): # 20 movements of 10 um maximum
                framelet = camera.snap()[y:y + size, x:x + size]

                ret, thresh = cv2.threshold(framelet, 127, 255, cv2.THRESH_BINARY)
                black_area = sum(thresh == 0)

                if i == 0:
                    init_area = black_area
                else:
                    increase = black_area - init_area
                    print increase
                    if increase > 25 / pixel_per_um ** 2:  # 5 x 5 um
                        print "Contact with water"
                        break

                calibrated_unit.relative_move(-10*calibrated_unit.up_direction[2],2) # 10 um down
                calibrated_unit.wait_until_still()

            print("Impaling the cell")
            calibrated_unit.relative_move(-50 * calibrated_unit.up_direction[2], 2)  # 50 um down
            calibrated_unit.wait_until_still()

            print("Done")
        except Exception:
            print(traceback.format_exc())

    @QtCore.pyqtSlot()
    def break_in(self): # Breaking in
        if (amplifier is None) | (pressure is None):
            print("Amplifier or pressure controller not available. Aborting.")
            return
        try:
            print("Breaking in")
            autopatcher.break_in(message)
            print("Done")
        except AutopatchError as e:
            print(str(e))
        except Exception:
            print(traceback.format_exc())

    @QtCore.pyqtSlot()
    def do_patch(self): # Start the patch-clamp procedure
        if (amplifier is None) | (pressure is None):
            print("Amplifier or pressure controller not available. Aborting.")
            return
        try:
            print("Starting patch-clamp")
            autopatcher.run(self.move_position, message)
            print("Done")
        except AutopatchError as e:
            print(str(e))
        except Exception:
            print(traceback.format_exc())

    @QtCore.pyqtSlot()
    def patch_without_move(self): # Start the patch-clamp procedure
        if (amplifier is None) | (pressure is None):
            print("Amplifier or pressure controller not available. Aborting.")
            return
        try:
            print("Starting patch-clamp, no pipette movement")
            autopatcher.run(move_position=None, message=message)
            print("Done")
        except AutopatchError as e:
            print(str(e))
        except Exception:
            print(traceback.format_exc())

    @QtCore.pyqtSlot()
    def pipette_back(self): # Move pipette back under the microscope
        try:
            print("Moving the pipette back under the microscope")
            calibrated_unit.move_new_pipette_back(message=message)
            print("Done")
        except Exception:
            print(traceback.format_exc())


    @QtCore.pyqtSlot()
    def move_pipette(self):
        try:
            calibrated_unit.safe_move(self.move_position, recalibrate=True) # just for testing here
            #calibrated_unit.auto_recalibrate(center=False)
            #calibrated_unit.reference_move(self.move_position)
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
            calibrated_unit.analyze_calibration()
        except Exception:
            print(traceback.format_exc())
        print('Done')

    @QtCore.pyqtSlot()
    def stage_calibrate(self):
        print('Starting stage calibration....')
        try:
            t1 = time.time()
            calibrated_stage.calibrate(message)
            t2 = time.time()
            print t2 - t1, 's'
            calibrated_unit.analyze_calibration()
        except Exception:
            print(traceback.format_exc())
        print('Done')

    @QtCore.pyqtSlot()
    def change_objective(self):
        print('New objective')
        oldM,oldMinv,oldr0 = calibrated_stage.M.copy(),\
                             calibrated_stage.Minv.copy(),\
                             calibrated_stage.r0.copy()
        pixel_per_um = calibrated_stage.pixel_per_um()[0]
        print('Starting stage calibration....')
        try:
            calibrated_stage.calibrate(message)
            calibrated_unit.analyze_calibration()
            magnification = calibrated_stage.pixel_per_um()[0]/pixel_per_um
            print magnification
            calibrated_unit.M[:2,:] = calibrated_unit.M[:2,:]*magnification
            calibrated_unit.Minv[:,:2] = calibrated_unit.Minv[:,:2]/magnification
            calibrated_unit.r0[:2] = calibrated_unit.r0[:2]*magnification
            calibrated_stage.M, calibrated_stage.Minv, calibrated_stage.r0 =\
                oldM, oldMinv, oldr0
            calibrated_stage.M[:2,:] = calibrated_stage.M[:2,:]*magnification
            calibrated_stage.Minv[:,:2] = calibrated_stage.Minv[:,:2]/magnification
            calibrated_stage.r0[:2] = calibrated_stage.r0[:2]*magnification
            calibrated_unit.analyze_calibration()
        except Exception:
            print(traceback.format_exc())

        print('Done')


    @QtCore.pyqtSlot()
    def manual_calibration(self):
        print('Manual calibration....')
        try:
            calibrated_unit.manual_calibration((landmark_r[-4:], landmark_u[-4:], landmark_rs[-4:]), message)
            calibrated_unit.analyze_calibration()
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
            calibrated_unit.auto_recalibrate(message=message, center = False)
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
        #print unit.min, unit.max
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

    ##### HOANG
    @QtCore.pyqtSlot()
    def do_cleaning_pipette(self):
        if (amplifier is None) | (pressure is None):
            print("Amplifier or pressure controller not available. Aborting.")
            return
        #Step 1: Washing.
        print('Cleaning the pipette: Started')
        try:
            #Move the pipette to the washing bath.
            calibrated_unit.absolute_move(u4[0],0)
            calibrated_unit.wait_until_still(0)
            calibrated_unit.absolute_move(u4[2]-5000, 2)
            calibrated_unit.wait_until_still(2)
            calibrated_unit.absolute_move(u4[1],1)
            calibrated_unit.wait_until_still(1)
            calibrated_unit.absolute_move(u4[2],2)
            calibrated_unit.wait_until_still(2)
            #Fill up with the Alconox
            pressure.set_pressure(-600)
            time.sleep(1)
            #5 cycles of tip cleaning
            for i in range (1,5):
                pressure.set_pressure(-600)
                time.sleep(0.625)
                pressure.set_pressure(1000)
                time.sleep(0.375)

            #Step 2: Rinsing.
            #Move the pipette to the rinsing bath.
            calibrated_unit.absolute_move(u5[2]-5000, 2)
            calibrated_unit.wait_until_still(2)
            calibrated_unit.absolute_move(u5[1], 1)
            calibrated_unit.wait_until_still(1)
            calibrated_unit.absolute_move(u5[0], 0)
            calibrated_unit.wait_until_still(0)
            calibrated_unit.absolute_move(u5[2], 2)
            calibrated_unit.wait_until_still(2)
            #Expel the remaining Alconox
            pressure.set_pressure(1000)
            time.sleep(6)

            #Step 3: Move back.
            calibrated_unit.absolute_move(0, 0)
            calibrated_unit.wait_until_still(0)
            calibrated_unit.absolute_move(u3[1], 1)
            calibrated_unit.wait_until_still(1)
            calibrated_unit.absolute_move(u3[2], 2)
            calibrated_unit.wait_until_still(2)
            calibrated_unit.absolute_move(u3[0], 0)
            calibrated_unit.wait_until_still(0)
            #Move microscope back to original position

            print("Done")
        except Exception:
            print(traceback.format_exc())

    @QtCore.pyqtSlot()
    def do_initial_location(self):
        print("Initial Location")
        try:
            microscope.absolute_move(z6)
            microscope.wait_until_still()
            calibrated_unit.absolute_move(u6)
            if us6 is not None:
                stage.absolute_move(us6)
            stage.wait_until_still()
            calibrated_unit.wait_until_still()

        except Exception:
            print(traceback.format_exc())
        print("Done")

    # @QtCore.pyqtSlot()
    # def do_movement_compensate(self):
    #     print("Initial Location")
    #     try:
    #         #calibrated_stage.reference_move
    #     except Exception:
    #         print(traceback.format_exc())
    #     print("Done")

    @QtCore.pyqtSlot()
    def do_move_patch_clean(self):
        global moveList
        if (amplifier is None) | (pressure is None):
            print("Amplifier or pressure controller not available. Aborting.")
            return
        try:
            print(moveList)
            for i in moveList:
                self.move_position = i
                calibrated_unit.safe_move(self.move_position, recalibrate=True)
                print("Done. Starting patch-clamp")
                amplifier.start_patch()
                # Pressure level 1
                pressure.set_pressure(param_pressure_near)

                # Check initial resistance
                amplifier.auto_pipette_offset()
                time.sleep(4.)
                R = amplifier.resistance()
                message("Resistance:" + str(R / 1e6))
                if R < param_Rmin:
                    raise AutopatchError("Resistance is too low (broken tip?)")
                elif R > param_Rmax:
                    raise AutopatchError("Resistance is too high (obstructed?)")

                # Pipette offset
                amplifier.auto_pipette_offset()
                time.sleep(2)  # why?

                # Approach and make the seal
                print("Approaching the cell")
                success = False
                oldR = R
                for _ in range(param_max_distance):  # move 15 um down
                    # move by 1 um down
                    # Cleaner: use reference relative move
                    calibrated_unit.relative_move(1, axis=2)  # *calibrated_unit.up_position[2]
                    calibrated_unit.wait_until_still(2)
                    self.move_position = i
                    calibrated_unit.safe_move(self.move_position, recalibrate=True)
                    time.sleep(1)
                    R = amplifier.resistance()
                    message("R = " + str(amplifier.resistance() / 1e6))
                    if R > oldR * (1 + param_cell_R_increase):  # R increases: near cell?
                        # Release pressure
                        message("Releasing pressure")
                        pressure.set_pressure(0)
                        time.sleep(10)
                        if R > oldR * (1 + param_cell_R_increase):
                            # Still higher, we are near the cell
                            message("Sealing, R = " + str(amplifier.resistance() / 1e6))
                            pressure.set_pressure(param_pressure_sealing)
                            t0 = time.time()
                            t = t0
                            R = amplifier.resistance()
                            while (R < param_gigaseal_R) | (t - t0 < param_seal_min_time):
                                # Wait at least 15s and until we get a Gigaseal
                                t = time.time()
                                if t - t0 < param_Vramp_duration:
                                    # Ramp to -70 mV in 10 s (default)
                                    self.amplifier.set_holding(param_Vramp_amplitude * (t - t0) / param_Vramp_duration)
                                if t - t0 >= param_seal_deadline:
                                    # No seal in 90 s
                                    amplifier.stop_patch()
                                    raise AutopatchError("Seal unsuccessful")
                                R = amplifier.resistance()
                            success = True
                            break
                pressure.set_pressure(0)
                if not success:
                    raise AutopatchError("Seal unsuccessful")
                print("Seal successful, R = " + str(self.amplifier.resistance() / 1e6))

                R = amplifier.resistance()
                if R < param_gigaseal_R:
                    raise AutopatchError("Seal lost")
                pressure = 0
                trials = 0
                while amplifier.resistance() > param_max_cell_R:  # Success when resistance goes below 300 MOhm
                    trials += 1
                    message('Essai ' + str(trials))
                    pressure += param_pressure_ramp_increment
                    if abs(pressure) > abs(param_pressure_ramp_max):
                        raise AutopatchError("Break-in unsuccessful")
                    if param_zap:
                        amplifier.zap()
                    pressure.ramp(amplitude=pressure, duration=param_pressure_ramp_duration)
                    time.sleep(1.3)
                message("Successful break-in, R = " + str(amplifier.resistance() / 1e6))
                amplifier.stop_patch()
                pressure.set_pressure(param_pressure_near)

                # Move the pipette to the washing bath.
                calibrated_unit.absolute_move(u4[0], 0)
                calibrated_unit.wait_until_still(0)
                calibrated_unit.absolute_move(u4[2] - 5000, 2)
                calibrated_unit.wait_until_still(2)
                calibrated_unit.absolute_move(u4[1], 1)
                calibrated_unit.wait_until_still(1)
                calibrated_unit.absolute_move(u4[2], 2)
                calibrated_unit.wait_until_still(2)
                # Fill up with the Alconox
                pressure.set_pressure(-600)
                time.sleep(1)
                # 5 cycles of tip cleaning
                for i in range(1, 5):
                    pressure.set_pressure(-600)
                    time.sleep(0.625)
                    pressure.set_pressure(1000)
                    time.sleep(0.375)

                # Step 2: Rinsing.
                # Move the pipette to the rinsing bath.
                calibrated_unit.absolute_move(u5[2] - 5000, 2)
                calibrated_unit.wait_until_still(2)
                calibrated_unit.absolute_move(u5[1], 1)
                calibrated_unit.wait_until_still(1)
                calibrated_unit.absolute_move(u5[0], 0)
                calibrated_unit.wait_until_still(0)
                calibrated_unit.absolute_move(u5[2], 2)
                calibrated_unit.wait_until_still(2)
                # Expel the remaining Alconox
                pressure.set_pressure(1000)
                time.sleep(6)

                #Step 3: Move back.
                calibrated_unit.absolute_move(0, 0)
                calibrated_unit.wait_until_still(0)
                calibrated_unit.absolute_move(u3[1], 1)
                calibrated_unit.wait_until_still(1)
                calibrated_unit.absolute_move(u3[2], 2)
                calibrated_unit.wait_until_still(2)
                calibrated_unit.absolute_move(u3[0], 0)
                calibrated_unit.wait_until_still(0)
                # Move microscope back to original position

            print("Done")
            moveList = []
        except Exception:
            print(traceback.format_exc())

    @QtCore.pyqtSlot()
    def do_nomove_patch_clean(self):
        global moveList
        if (amplifier is None) | (pressure is None):
            print("Amplifier or pressure controller not available. Aborting.")
            return
        try:
            print(moveList)
            for i in moveList:
                print("Done. Starting patch-clamp")
                amplifier.start_patch()
                # Pressure level 1
                pressure.set_pressure(param_pressure_near)

                # Check initial resistance
                amplifier.auto_pipette_offset()
                time.sleep(4.)
                R = amplifier.resistance()
                message("Resistance:" + str(R / 1e6))
                if R < param_Rmin:
                    raise AutopatchError("Resistance is too low (broken tip?)")
                elif R > param_Rmax:
                    raise AutopatchError("Resistance is too high (obstructed?)")

                # Pipette offset
                amplifier.auto_pipette_offset()
                time.sleep(2)  # why?

                # Approach and make the seal
                print("Approaching the cell")
                success = False
                oldR = R
                for _ in range(param_max_distance):  # move 15 um down
                    # move by 1 um down
                    # Cleaner: use reference relative move
                    calibrated_unit.relative_move(1, axis=2)  # *calibrated_unit.up_position[2]
                    calibrated_unit.wait_until_still(2)
                    time.sleep(1)
                    R = amplifier.resistance()
                    message("R = " + str(amplifier.resistance() / 1e6))
                    if R > oldR * (1 + param_cell_R_increase):  # R increases: near cell?
                        # Release pressure
                        message("Releasing pressure")
                        pressure.set_pressure(0)
                        time.sleep(10)
                        if R > oldR * (1 + param_cell_R_increase):
                            # Still higher, we are near the cell
                            message("Sealing, R = " + str(amplifier.resistance() / 1e6))
                            pressure.set_pressure(param_pressure_sealing)
                            t0 = time.time()
                            t = t0
                            R = amplifier.resistance()
                            while (R < param_gigaseal_R) | (t - t0 < param_seal_min_time):
                                # Wait at least 15s and until we get a Gigaseal
                                t = time.time()
                                if t - t0 < param_Vramp_duration:
                                    # Ramp to -70 mV in 10 s (default)
                                    self.amplifier.set_holding(param_Vramp_amplitude * (t - t0) / param_Vramp_duration)
                                if t - t0 >= param_seal_deadline:
                                    # No seal in 90 s
                                    amplifier.stop_patch()
                                    raise AutopatchError("Seal unsuccessful")
                                R = amplifier.resistance()
                            success = True
                            break
                pressure.set_pressure(0)
                if not success:
                    raise AutopatchError("Seal unsuccessful")
                print("Seal successful, R = " + str(self.amplifier.resistance() / 1e6))

                R = amplifier.resistance()
                if R < param_gigaseal_R:
                    raise AutopatchError("Seal lost")
                pressure = 0
                trials = 0
                while amplifier.resistance() > param_max_cell_R:  # Success when resistance goes below 300 MOhm
                    trials += 1
                    message('Essai ' + str(trials))
                    pressure += param_pressure_ramp_increment
                    if abs(pressure) > abs(param_pressure_ramp_max):
                        raise AutopatchError("Break-in unsuccessful")
                    if param_zap:
                        amplifier.zap()
                    pressure.ramp(amplitude=pressure, duration=param_pressure_ramp_duration)
                    time.sleep(1.3)
                message("Successful break-in, R = " + str(amplifier.resistance() / 1e6))
                amplifier.stop_patch()
                pressure.set_pressure(param_pressure_near)

                # Move the pipette to the washing bath.
                calibrated_unit.absolute_move(u4[0], 0)
                calibrated_unit.wait_until_still(0)
                calibrated_unit.absolute_move(u4[2] - 5000, 2)
                calibrated_unit.wait_until_still(2)
                calibrated_unit.absolute_move(u4[1], 1)
                calibrated_unit.wait_until_still(1)
                calibrated_unit.absolute_move(u4[2], 2)
                calibrated_unit.wait_until_still(2)
                # Fill up with the Alconox
                pressure.set_pressure(-600)
                time.sleep(1)
                # 5 cycles of tip cleaning
                for i in range(1, 5):
                    pressure.set_pressure(-600)
                    time.sleep(0.625)
                    pressure.set_pressure(1000)
                    time.sleep(0.375)

                # Step 2: Rinsing.
                # Move the pipette to the rinsing bath.
                calibrated_unit.absolute_move(u5[2] - 5000, 2)
                calibrated_unit.wait_until_still(2)
                calibrated_unit.absolute_move(u5[1], 1)
                calibrated_unit.wait_until_still(1)
                calibrated_unit.absolute_move(u5[0], 0)
                calibrated_unit.wait_until_still(0)
                calibrated_unit.absolute_move(u5[2], 2)
                calibrated_unit.wait_until_still(2)
                # Expel the remaining Alconox
                pressure.set_pressure(1000)
                time.sleep(6)

                #Step 3: Move back.
                calibrated_unit.absolute_move(0, 0)
                calibrated_unit.wait_until_still(0)
                calibrated_unit.absolute_move(u3[1], 1)
                calibrated_unit.wait_until_still(1)
                calibrated_unit.absolute_move(u3[2], 2)
                calibrated_unit.wait_until_still(2)
                calibrated_unit.absolute_move(u3[0], 0)
                calibrated_unit.wait_until_still(0)
                # Move microscope back to original position

            print("Done")
            moveList = []
        except Exception:
            print(traceback.format_exc())

    @QtCore.pyqtSlot()
    def do_testing_calibration(self):
        print('Starting calibration....')
        try:
            t1 = time.time()
            #calibrated_stage.calibrate()
            #calibrated_unit.calibrate_with_stage(message)
            calibrated_unit.calibrate3(message)
            t2 = time.time()
            print t2 - t1, 's'
            calibrated_unit.analyze_calibration()
        except Exception:
            print(traceback.format_exc())
        print('Done')

    @QtCore.pyqtSlot()
    def take_testing_photos(self):
        global stack,x0,y0
        print("Taking photos")
        try:
            calibrated_unit.take_photos2(message)
        except Exception:
            print(traceback.format_exc())
        print("Done")

    @QtCore.pyqtSlot()
    def test_cardinal_positions(self):
        global stack, x0, y0
        print("Test cardinal positions")
        try:
            calibrated_unit.take_photos3(message)
        except Exception:
            print(traceback.format_exc())
        print("Done")

# class Tracker(QtCore.QObject):
#
#      @QtCore.pyqtSlot()
#      def do_tracking(self):
#          while True:
#              frame = camera.snap()
#              ok, boxes = self.multitracker.update(frame)
#              for newbox in boxes:
#                 p1 = (int(newbox[0]), int(newbox[1]))
#                 p2 = (int(newbox[0] + newbox[2]), int(newbox[1] + newbox[3]))
#                 cv2.rectangle(frame, p1, p2, (200, 0, 0))


class ImageEditor(object): # adds stuff on the image, including paramecium tracker
    def __init__(self):
        self.show_paramecium = False

    def point_paramecium(self, img):
        global paramecium_x, paramecium_y

        x,y,theta = where_is_paramecium(img, calibrated_stage.pixel_per_um()[0], return_angle=True,
                                        previous_x=None, previous_y=None)

        if x is not None:
            x, y = int(x), int(y)
            cv2.circle(img, (x,y), 50, (0, 0, 255))
            # Draw segment to indicate angle
            cv2.line(img,(x,y),(x+int(50*cos(theta)),y+int(50*sin(theta))),(0, 0, 255))
            # and track
            xs = x - img.shape[1] / 2
            ys = y - img.shape[0] / 2
            gain = 0.5
            #calibrated_stage.reference_relative_move(-gain*array([xs,ys,0]))
            paramecium_x, paramecium_y = x,y

        return img

    def edit_image(self, img):
        # Draws the centroid of the image
        # maybe first a laplacian? (local contrast)
        #normalizedImg = zeros((800, 800))
        #normalizedImg = cv2.normalize(img, normalizedImg, 0, 255, cv2.NORM_MINMAX)

        # Find the centroid (doesn't give the tip)
        #xy = mgrid[0:normalizedImg.shape[0], 0:normalizedImg.shape[1]]
        #yc = int(sum(xy[0] * normalizedImg) / sum(normalizedImg))
        #xc = int(sum(xy[1] * normalizedImg) / sum(normalizedImg))

        #cv2.line(img,(xc-5,yc),(xc+5,yc),(0, 0, 255))
        #cv2.line(img,(xc,yc-5),(xc,yc-5),(0, 0, 255))

        # Tracks paramecium
        if self.show_paramecium:
            img = self.point_paramecium(img)
        
        return img

image_editor = ImageEditor()

def message(msg):
    print msg

def image_edit(img):
    return image_editor.edit_image(img)

def display_edit(img):
    draw_cross(img)
    draw_bar(img, int(calibrated_stage.pixel_per_um()[0]*10))

# Start amplifier and pressure controller
# If not available, run anyway without them

##### HOANG
z3,u3,u4,u5 = None, None, None, None
u6 = None
us6 = None
z6 = None
moveList = []
amplifier, pressure = None, None
try:
    amplifier = MultiClampChannel()
except Exception:
    print(traceback.format_exc())
try:
    pressure = OB1()
    pressure.set_pressure(25)
except Exception:
    print(traceback.format_exc())

paramecium_x, paramecium_y = None, None

calibrated_unit = calibrated_units[0]

autopatcher = AutoPatcher(amplifier, pressure, calibrated_unit)
stack = None
x0, y0 = None, None
boxes = None
landmark_u = [] # Landmark points
landmark_r = []
landmark_rs = []
axes_end = [] # End points of axes

app = QtWidgets.QApplication(sys.argv)
gui = TestGui(camera)
gui.show()
ret = app.exec_()

sys.exit(ret)