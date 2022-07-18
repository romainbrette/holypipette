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
        super(LucamCamera, self).__init__()

        self.cam = Lucam()
        self.cam.CameraReset()

        self.exposure = exposure
        self.gain = gain

        default = self.cam._default_frameformat

        if width is None:
            width = default.width
        if height is None:
            height = default.height
        self.width = width
        self.height = height

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
        self.gain = gain
        snapshot = self.update_exposure_gain(exposure, gain)

        self.cam.EnableFastFrames(snapshot)

        self.start_acquisition()

    def update_exposure_gain(self, exposure, gain):
        frameformat, framerate = self.cam.GetFormat()
        print("Frame rate: {} Hz".format(framerate))
        snapshot = self.cam.default_snapshot()
        if exposure is not None:
            snapshot.exposure = exposure
        if gain is not None:
            snapshot.gain = gain
        snapshot.format = frameformat
        return snapshot

    def __del__(self):
        try:
            self.cam.DisableFastFrames()
            self.cam.CameraClose()
            del self.cam
        except Exception:
            pass

    def raw_snap(self):
        return self.cam.TakeFastFrame(validate=False)

    def set_exposure(self, value):
        # setting exposure time requires setting it in a snapshot
        # so we have to stop the fast frame acquisition
        self.cam.DisableFastFrames()
        self.cam.exposure = value
        snapshot = self.update_exposure_gain(exposure=value, gain=self.gain)
        self.cam.EnableFastFrames(snapshot)

    def get_exposure(self):
        return self.cam.exposure
