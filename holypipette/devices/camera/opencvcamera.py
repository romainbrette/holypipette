'''
Camera access using OpenCv
'''
import numpy as np
import time

from .camera import *
import warnings

try:
    import cv2
except ImportError:
    warnings.warn('OpenCV is not installed.')

__all__ = ['OpenCVCamera']


class OpenCVCamera(Camera):
    def __init__(self, width=None, height=None):
        self.video = cv2.VideoCapture(0)
        if width is not None:
            self.video.set(3, width)
        if height is not None:
            self.video.set(4, height)
        self.width = int(self.video.get(3))
        self.height = int(self.video.get(4))

    def __del__(self):
        self.video.release()

    def reset(self):
        self.video.open(0)

    def snap(self):
        '''
        Returns the current image.
        This is a blocking call (wait until next frame is available)
        '''
        ret, frame = self.video.read()
        if frame is None:
            raise IOError('OpenCV did not receive any frame (error code %d)' % ret)
        if frame.dtype == 'uint16':
            frame = cv2.convertScaleAbs(frame, alpha=2 ** -2)
        else:
            frame = cv2.convertScaleAbs(frame)
        return np.array(frame[:, :, 0])
