from __future__ import print_function
'''
A camera using Lucam
'''
import collections
import os
import sys
import threading
import warnings
from time import sleep, time
import PIL

from .lucam import Lucam, API, LucamError
from .camera import *

__all__ = ['LucamCamera']

class LucamCamera(Camera):
    def __init__(self, exposure=None, gain=None, binning=1, x=0, y=0, width=None, height=None, depth=8):
        self.cam = Lucam()
        self.cam.CameraReset()

        self.exposure = exposure
        self.gain = gain

        default = self.cam._default_frameformat
        if width is None:
            width = default.width
        if height is None:
            height = default.height
        if depth == 16:
            depth = API.LUCAM_PF_16
        elif depth == 8:
            depth = API.LUCAM_PF_8
        self.cam.SetFormat(
            Lucam.FrameFormat(int(x*1. / (16 * binning)) * 16 * binning,
                              int(y * 1. / (16 * binning)) * 16 * binning,
                              int(width*1. / (16 * binning)) * 16 * binning,
                              int(height*1. / (16 * binning)) * 16 * binning,
                              depth,  # API.LUCAM_PF_8,
                              binningX=binning, binningY=binning),
            framerate=100.0)
        frameformat, framerate = self.cam.GetFormat()
        print("Frame rate: {} Hz".format(framerate))

        snapshot = self.cam.default_snapshot()
        snapshot.exposure = exposure
        snapshot.gain = gain
        snapshot.format = frameformat
        
        self.cam.frame = self.cam.TakeSnapshot()
        self.cam.EnableFastFrames(snapshot)

    def __del__(self):
        try:
            self.cam.DisableFastFrames()
            self.cam.CameraClose()
            del self.cam
        except Exception:
            pass

    def raw_snap(self):
        return self.cam.TakeFastFrame()
    
    def set_exposure(self, value):
        self.cam.set_properties(exposure=value)
    
    def get_exposure(self):
        return self.cam.exposure
