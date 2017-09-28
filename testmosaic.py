'''
Test mosaic photos
'''
from devices import *
from vision import *
from gui import *
import cv2
import time
from numpy import array
import pylab

def callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        xs = x-camera.width/2
        ys = y-camera.height/2
        print xs, ys
        calibrated_stage.reference_move(calibrated_stage.reference_position()-array([xs, ys, 0]))

#camera = OpenCVCamera()
camera = Lumenera()
#video = LiveFeed(camera, mouse_callback=callback)

controller = LuigsNeumann_SM10(stepmoves=False)
stage = ManipulatorUnit(controller,[7,8])
microscope = Microscope(controller,9)
calibrated_stage = CalibratedStage(stage, None, microscope, camera=camera)
#unit = ManipulatorUnit(controller, [1,2,3])
#calibrated_unit = CalibratedUnit(unit, calibrated_stage, microscope, camera=camera)
#calibrated_unit = CalibratedUnit(unit, None, microscope, camera=camera)

def message(msg):
    print msg

"""
try:

    cv2.waitKey(0)
    u0_stage = stage.position()
    z0 = microscope.position()

    t1 = time.time()
    calibrated_stage.calibrate()
    t2 = time.time()
    print "Calibration took",t2-t1,"s"
    print calibrated_stage.M, calibrated_stage.r0

    cv2.waitKey(0)

    print camera.width,camera.height
    t1 = time.time()
    mosaic = calibrated_stage.mosaic(camera.width*3,camera.height*3)
    t2 = time.time()
    print mosaic.shape
    print "Mosaic took", t2 - t1, "s"

    cv2.waitKey(0)


finally:
    microscope.absolute_move(z0)
    stage.absolute_move(u0_stage)
    video.stop()
"""

t1 = time.time()
calibrated_stage.calibrate()
t2 = time.time()
print "Calibration took", t2 - t1, "s"
print calibrated_stage.M, calibrated_stage.r0
t1 = time.time()
mosaic = calibrated_stage.mosaic(camera.width * 3, camera.height * 3)
t2 = time.time()
print mosaic.shape
print "Mosaic took", t2 - t1, "s"

pylab.imshow(mosaic[::5,::5], cmap = 'gray')
pylab.show()
