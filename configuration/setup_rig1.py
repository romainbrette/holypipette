'''
Setup script for the first rig with the LN SM-10
'''
from devices.camera.umanagercamera import Lumenera
from devices.manipulator import *

camera = Lumenera()
controller = LuigsNeumann_SM10(stepmoves=True)
stage = ManipulatorUnit(controller, [7, 8])
microscope = Microscope(controller, 9)
calibrated_stage = CalibratedStage(stage, None, microscope, camera=camera)
unit = ManipulatorUnit(controller, [1, 2, 3])
calibrated_unit = CalibratedUnit(unit, calibrated_stage, microscope, camera=camera)
