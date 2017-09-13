'''
This is a test GUI, to test the functionality
'''
from devices import *
from vision import *
from gui import *

camera = OpenCVCamera()
livefeed = LiveFeed(camera)

raw_input("Press Enter to continue...")

livefeed.stop()
