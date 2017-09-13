'''
This is a test GUI, to test the functionality
'''
from devices import *
from vision import *
from gui import *
import cv2

def callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        xs = x-camera.width/2
        ys = y-camera.height/2
        print xs, ys

camera = OpenCVCamera()
livefeed = LiveFeed(camera, mouse_callback=callback)

controller = FakeManipulator() #LuigsNeumann_SM10()
stage = ManipulatorUnit(controller,[7,8])
microscope = ManipulatorUnit(controller,[9])
calibrated_stage = CalibratedUnit(stage, None, microscope, camera=camera, horizontal=True)

cv2.waitKey(0)

livefeed.stop()

