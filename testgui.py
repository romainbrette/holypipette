'''
This is a test GUI, to test the functionality
'''
from devices import *
from vision import *
from gui import *
from threading import Thread
import cv2

def callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print x, y

camera = OpenCVCamera()
livefeed = LiveFeed(camera, mouse_callback=callback) # callback doesn't work, why?

cv2.waitKey(0)

livefeed.stop()

