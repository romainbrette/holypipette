'''
A generic camera class

TODO:
* A stack() method which takes a series of photos along Z axis
'''
import numpy as np
import scipy.misc

__all__ = ['Camera', 'FakeCamera']


class Camera(object):
    def __init__(self):
        self.width = 1000
        self.height = 1000

    def new_frame(self):
        '''
        Returns True if a new frame is available
        '''
        return True

    def snap(self):
        '''
        Returns the current image
        '''
        return None

    def set_exposure(self, value):
        print('Setting exposure time not supported for this camera')

    def get_exposure(self):
        print('Getting exposure time not supported for this camera')
        return -1

    def change_exposure(self, change):
        if self.get_exposure() > 0:
            self.set_exposure(self.get_exposure() + change)

    def reset(self):
        pass


class FakeCamera(Camera):
    # TODO: Connect this to FakeManipulator etc.
    def __init__(self, width=None, height=None, dummy=False):
        self.width = 1024
        self.height = 768
        self.frame = scipy.misc.face(gray=True)
        self.exposure_time = 30

    def set_exposure(self, value):
        print value
        if 0 < value <= 200:
            self.exposure_time = value

    def get_exposure(self):
        return self.exposure_time

    def snap(self):
        '''
        Returns the current image.
        This is a blocking call (wait until next frame is available)
        '''
        exposure_factor = self.exposure_time/30.
        noisy_frame = self.frame + np.random.randn(self.height, self.width)*10
        return np.array(np.clip(noisy_frame*exposure_factor, 0, 255),
                        dtype=np.uint8)
