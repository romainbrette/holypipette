'''
This is a test GUI, to test the functionality
'''
from devices import *
from vision import *
from gui import *

def callback(event, x, y, flags, param):
    print x, y

camera = OpenCVCamera()
livefeed = LiveFeed(camera, mouse_callback=callback) # callback doesn't work, why?

raw_input("Press Enter to continue...")

livefeed.stop()
