'''
A camera using micromanager.

TODO:
* the path is hard-coded: should be in configuration file
* there is one class per camera, it should just read umanager's config file
'''
from camera import *
import sys
import warnings
sys.path.append('C:\\Program Files\\Micro-Manager-1.4')
try:
    import MMCorePy
except ImportError:
    # Micromanager not installed
    warnings.warn('Micromanager is not installed.')

__all__ = ['uManagerCamera']

class uManagerCamera(Camera):
    def __init__(self, brand, name, exposure):
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
        return self.cam.getLastImage() # What happens if there is no new frame?

class Hamamatsu(Camera):
    def __init__(self):
        uManagerCamera.__init__(self, 'HamamatsuHam', 'HamamatsuHam_DCAM', 60)

class Lumenera(Camera):
    def __init__(self):
        uManagerCamera.__init__(self, 'Lumenera', 'LuCam', 30)
