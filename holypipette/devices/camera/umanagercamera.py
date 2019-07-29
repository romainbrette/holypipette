'''
A camera using micromanager.

TODO:
* the path is hard-coded: should be in configuration file
* there is one class per camera, it should just read umanager's config file
'''
from __future__ import print_function
import sys
import threading
import warnings
import cv2
from time import sleep, time
import numpy as np

from .camera import *

#sys.path.append('C:\\Program Files\\Micro-Manager-1.4')
sys.path.append('C:\\Program Files\\Micro-Manager-2.0')
try:
    import MMCorePy
except ImportError:
    warnings.warn('Micromanager is not installed.')

__all__ = ['uManagerCamera', 'Hamamatsu', 'Lumenera']

class uManagerCamera(Camera):
    def __init__(self, brand, name, exposure):
        self.lock = threading.RLock()
        self.cam = MMCorePy.CMMCore()
        self.cam.loadDevice('Camera', brand, name)
        self.cam.initializeDevice('Camera')
        self.cam.setCameraDevice('Camera')
        if self.cam.hasProperty('Camera', 'Exposure') and not self.cam.isPropertyReadOnly('Camera', 'Exposure'):
            self.min_exposure = self.cam.getPropertyLowerLimit('Camera', 'Exposure')
            self.max_exposure = self.cam.getPropertyUpperLimit('Camera', 'Exposure')
            self.cam.setExposure(exposure)
            self.supports_exposure = True
        else:
            print('Camera does not support setting the exposure time')
            self.supports_exposure = False

        self.width, self.height = self.cam.getImageWidth(), self.cam.getImageHeight()

        self.cam.startContinuousSequenceAcquisition(1)

        # Keep an old frame around to detect a frozen image
        self.comparison_time = None
        self.comparison_frame = None

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
        frame = self.cam.getLastImage()  # What happens if there is no new frame?
        self.lock.release()

        # Check that the image is not frozen
        # now = time()
        # if self.comparison_time is None:
        #     self.comparison_time = now
        #     self.comparison_frame = frame
        # elif (now - self.comparison_time) > 1:
        #     if np.all(self.comparison_frame == frame):
        #         print('Camera image is *exactly* the same as 1s ago -- resetting camera!')
        #         self.reset()
        #     self.comparison_time = now
        #     self.comparison_frame = frame

        if frame.dtype == 'uint16':
            frame = cv2.convertScaleAbs(frame, alpha=2 ** -2)
        else:
            frame = cv2.convertScaleAbs(frame)
        return frame

    def set_exposure(self, value):
        if not self.supports_exposure:
            return
        if self.min_exposure <= value <= self.max_exposure:
            self.lock.acquire()
            self.cam.setExposure(value)
            self.lock.release()

    def get_exposure(self):
        if not self.supports_exposure:
            return -1
        self.lock.acquire()
        exposure = self.cam.getExposure()
        self.lock.release()
        return exposure

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
