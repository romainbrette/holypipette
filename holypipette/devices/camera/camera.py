'''
A generic camera class

TODO:
* A stack() method which takes a series of photos along Z axis
'''
from __future__ import print_function
import numpy as np
import scipy.misc
from scipy.ndimage.filters import gaussian_filter
from scipy.ndimage import fourier_gaussian

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
        self.exposure_time = 30
        self.manipulator = manipulator
        self.image_z = image_z
        self.scale_factor = 2.  # micrometers in pixels
        self.depth_of_field = 2.
        self.frame = np.array(np.clip(gaussian_filter(np.random.randn(self.width * 2, self.height * 2), 10)*50 + 128, 0, 255), dtype=np.uint8)

    def set_exposure(self, value):
        if 0 < value <= 200:
            self.exposure_time = value

    def get_exposure(self):
        return self.exposure_time

    def get_microscope_image(self, x, y, z):
        frame = np.roll(self.frame, int(y), axis=0)
        frame = np.roll(frame, int(x), axis=1)
        frame = frame[self.height//2:self.height//2+self.height,
                      self.width//2:self.width//2+self.width]
        return np.array(frame, copy=True)

    def snap(self):
        '''
        Returns the current image.
        This is a blocking call (wait until next frame is available)
        '''
        if self.manipulator is not None:
            # Use the part of the image under the microscope

            stage_x, stage_y, stage_z = self.manipulator.position_group([7, 8, 9])
            stage_z -= self.image_z
            stage_x *= self.scale_factor
            stage_y *= self.scale_factor
            stage_z *= self.scale_factor
            frame = self.get_microscope_image(stage_x, stage_y, stage_z)

            for direction, axes in [(np.pi/2, [1, 2, 3]),
                                    (-np.pi/2, [4, 5, 6])]:
                manipulators = np.zeros((self.height, self.width), dtype=np.int16)
                x, y, z = self.manipulator.position_group(axes)
                # Quick&dirty 3D transformation
                x = np.cos(self.manipulator.angle)*(x + 50/self.scale_factor)
                z = np.sin(self.manipulator.angle)*(x + 50/self.scale_factor) + z
                # scale
                x *= self.scale_factor
                y *= self.scale_factor
                z *= self.scale_factor
                # cut off a tip
                # Position relative to stage
                x -= stage_x
                y -= stage_y
                z -= stage_z
                X, Y = np.meshgrid(np.arange(self.width) - self.width/2 + x,
                                   np.arange(self.height) - self.height/2 + y)
                angle = np.arctan2(X, Y)
                dist = np.sqrt(X**2 + Y**2)
                border = (0.075 + 0.0025 * abs(z) / self.depth_of_field)
                manipulators[(np.abs(angle - direction) < border) & (dist > 50)] = 5
                edge_width = 0.02 if z > 0 else 0.04  # Make a distinction between below and above
                manipulators[(np.abs(angle - direction) < border) & (np.abs(angle - direction) > border-edge_width) & (dist > 50)] = 75
                frame[manipulators>0] = manipulators[manipulators>0]
        else:
            frame = scipy.misc.imresize(self.frame, size=0.5)
        exposure_factor = self.exposure_time/30.
        frame = frame + np.random.randn(self.height, self.width)*10
        return np.array(np.clip(frame*exposure_factor, 0, 255),
                        dtype=np.uint8)
