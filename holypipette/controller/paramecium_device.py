from .base import TaskController
from time import sleep
from scipy.optimize import golden, minimize_scalar
from numpy import array,arange

class ParameciumDeviceController(TaskController):
    def __init__(self, calibrated_unit, microscope,
                 calibrated_stage, camera, config):
        super(ParameciumDeviceController, self).__init__()
        self.config = config
        self.calibrated_unit = calibrated_unit
        self.calibrated_stage = calibrated_stage
        self.microscope = microscope
        self.camera = camera
