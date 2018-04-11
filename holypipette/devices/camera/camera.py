'''
A generic camera class

TODO:
* A stack() method which takes a series of photos along Z axis
'''
from __future__ import print_function
import numpy as np
import scipy.misc
from scipy.ndimage.filters import gaussian_filter

__all__ = ['Camera', 'FakeCamera']


class Camera(object):
    def __init__(self):
        super(Camera, self).__init__()
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
    def __init__(self, manipulator=None, image_z=0):
        super(FakeCamera, self).__init__()
        self.width = 1024
        self.height = 768
        self.frame = scipy.misc.imresize(scipy.misc.face(gray=True), size=2.0,
                                         interp='bicubic')  #.astype(np.int32)/2 + 125
        self.exposure_time = 30
        self.manipulator = manipulator
        self.image_z = image_z
        self.scale_factor = 3

    def set_exposure(self, value):
        if 0 < value <= 200:
            self.exposure_time = value

    def get_exposure(self):
        return self.exposure_time

    def snap(self):
        '''
        Returns the current image.
        This is a blocking call (wait until next frame is available)
        '''
        if self.manipulator is not None:
            # Use the part of the image under the microscope
            full_height, full_width = self.frame.shape[:2]
            stage_x, stage_y, stage_z = self.manipulator.position_group([7, 8, 9])
            stage_z -= self.image_z
            stage_x *= self.scale_factor
            stage_y *= self.scale_factor
            stage_z *= self.scale_factor
            frame = np.array(self.frame[int(full_height/2-stage_y-self.height/2):int(full_height/2-stage_y+self.height/2),
                             int(full_width/2-stage_x-self.width/2):int(full_width/2-stage_x+self.width/2)],
                             copy=True, dtype=np.int16)
            if stage_z != 0:
                frame = gaussian_filter(frame, abs(stage_z)/10.)
            for direction, axes in [(np.pi/2, [1, 2, 3]),
                                    (-np.pi/2, [4, 5, 6])]:
                manipulators = np.zeros((self.height, self.width), dtype=np.int16)
                x, y, z = self.manipulator.position_group(axes)
                # cut off a tip
                x += np.cos(direction)*15
                y += np.sin(direction)*15
                # Position relative to stage
                x -= stage_x
                y -= stage_y
                z -= stage_z
                # scale
                x *= self.scale_factor
                y *= self.scale_factor
                z *= self.scale_factor
                X, Y = np.meshgrid(np.arange(self.width) - self.width/2 + x,
                                   np.arange(self.height) - self.height/2 + y)
                angle = np.arctan2(X, Y)
                dist = np.sqrt(X**2 + Y**2)
                manipulators[(np.abs(angle-direction) < 0.075) & (dist > 50)] = 5
                if z != 0:
                    manipulators = gaussian_filter(manipulators, abs(z)/10.)
                frame[manipulators>0] = manipulators[manipulators>0]
        else:
            frame = scipy.misc.imresize(self.frame, size=0.5)
        exposure_factor = self.exposure_time/30.
        noisy_frame = frame + np.random.randn(self.height, self.width)*10
        return np.array(np.clip(noisy_frame*exposure_factor, 0, 255),
                        dtype=np.uint8)
