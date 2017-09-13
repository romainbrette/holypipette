'''
This is a test GUI, to test the functionality.

Seems to work, except the camera apparently doesn't start until waitkey (??)
'''
from devices import *
from vision import *
from gui import *
import cv2
import time

def callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        xs = x-camera.width/2
        ys = y-camera.height/2
        print xs, ys

#camera = OpenCVCamera()
camera = Lumenera()
video = LiveFeed(camera, mouse_callback=callback)

controller = LuigsNeumann_SM10()
stage = ManipulatorUnit(controller,[7,8])
microscope = ManipulatorUnit(controller,[9])
calibrated_stage = CalibratedUnit(stage, None, microscope, camera=camera, horizontal=True)

print stage.position(), microscope.position()

time.sleep(1)
stage.relative_move(10, 0)
stage.wait_until_still(0)
print stage.position(), microscope.position()

time.sleep(1)
microscope.relative_move(-10, 0)
microscope.wait_until_still(0)
print stage.position(), microscope.position()

time.sleep(1)
stage.relative_move(-10, 0)
microscope.relative_move(10, 0)
microscope.wait_until_still(0)
stage.wait_until_still(0)
print stage.position(), microscope.position()

cv2.waitKey(0)

video.stop()

