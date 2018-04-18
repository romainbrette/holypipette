"""
Package defining `TaskController` classes. Objects of these classes are
responsible for the high-level logic of controlling the hardware, e.g. dealing
with the calibration of a manipulator, or defining the procedure for an
automatic patch clamp experiment.
"""
from .base import *
from .patch import *