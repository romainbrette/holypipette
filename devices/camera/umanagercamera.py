'''
A camera using micromanager.

TODO:
* the path is hard-coded: should be in configuration file
* there is one class per camera, it should just read umanager's config file
'''
from camera import *
import sys
import threading
import warnings
import cv2
from time import sleep
sys.path.append('C:\\Program Files\\Micro-Manager-1.4')
try:
    import MMCorePy
except ImportError:
    warnings.warn('Micromanager is not installed.')

__all__ = ['uManagerCamera', 'Hamamatsu', 'Lumenera']

class uManagerCamera(Camera):
    def __init__(self, brand, name, exposure):
        self.lock = threading.Lock()
        self.cam = MMCorePy.CMMCore()
        self.cam.loadDevice('Camera', brand, name)
        self.cam.initializeDevice('Camera')
        self.cam.setCameraDevice('Camera')
        self.cam.setExposure(exposure)
        self.width, self.height = self.cam.getImageWidth(), self.cam.getImageHeight()

        self.cam.startContinuousSequenceAcquisition(1)
        # An alternative is to use snapimage / getimage

    def __del__(self):
        self.cam.stopSequenceAcquisition()
        self.cam.unloadDevice('Camera')

    def new_frame(self):
        '''
        Returns True if a new frame is available
        '''
        return (self.cam.getRemainingImageCount() > 0)

    def snap(self):
        self.lock.acquire()
        while not self.new_frame():
            sleep(0.01)
            print "ouch"
        frame = self.cam.getLastImage() # What happens if there is no new frame?
        self.lock.release()
        if frame.dtype == 'uint16':
            frame = cv2.convertScaleAbs(frame, alpha=2 ** -2)
        else:
            frame = cv2.convertScaleAbs(frame)
        return frame

class Hamamatsu(uManagerCamera):
    def __init__(self):
        uManagerCamera.__init__(self, 'HamamatsuHam', 'HamamatsuHam_DCAM', 10)

class Lumenera(uManagerCamera):
    def __init__(self):
        uManagerCamera.__init__(self, 'Lumenera', 'LuCam', 30)
