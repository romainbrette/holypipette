'''
Camera access using OpenCv
'''
from camera import *
import warnings

try:
    import cv2
except ImportError:
    warnings.warn('OpenCV is not installed.')

__all__ = ['OpenCVCamera']


class OpenCVCamera(Camera):
    def __init__(self):
        self.video = cv2.VideoCapture(0)
        self.width = int(self.video.get(3))
        self.height = int(self.video.get(4))

    def __del__(self):
        self.video.release()

    def snap(self):
        '''
        Returns the current image.
        This is a blocking call (wait until next frame is available)
        '''
        _, frame = self.video.read()
        return frame
