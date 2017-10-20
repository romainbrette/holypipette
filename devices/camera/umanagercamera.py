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
        self.min_exposure = self.cam.getPropertyLowerLimit('Camera', 'Exposure')
        self.max_exposure = self.cam.getPropertyUpperLimit('Camera', 'Exposure')
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
            sleep(0.05)
            print("no image available, waiting for 5ms")
        frame = self.cam.getLastImage() # What happens if there is no new frame?
        self.lock.release()
        if frame.dtype == 'uint16':
            frame = cv2.convertScaleAbs(frame, alpha=2 ** -2)
        else:
            frame = cv2.convertScaleAbs(frame)
        return frame

    def set_exposure(self, value):
        if self.min_exposure <= value <= self.max_exposure:
            self.cam.setExposure(value)

    def get_exposure(self):
        return self.cam.getExposure()

    def reset(self):
        print('Resetting image acquisition...')
        self.lock.acquire()
        self.cam.stopSequenceAcquisition()
        self.cam.startContinuousSequenceAcquisition(1)
        self.lock.release()
        print('...done')

class Hamamatsu(uManagerCamera):
    def __init__(self):
        uManagerCamera.__init__(self, 'HamamatsuHam', 'HamamatsuHam_DCAM', 10)

class Lumenera(uManagerCamera):
    def __init__(self):
        uManagerCamera.__init__(self, 'Lumenera', 'LuCam', 30)
