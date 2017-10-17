'''
Setup script for the first rig with the LN SM-5
'''
from devices.camera.umanagercamera import Hamamatsu
from devices.manipulator import *

camera = Hamamatsu()
controller = LuigsNeumann_SM5(name='COM3', stepmoves=True)
stage = ManipulatorUnit(controller,[7,8])
microscope = Leica()
unit = ManipulatorUnit(controller, [1,2,3])
calibrated_stage = CalibratedStage(stage, None, microscope, camera=camera)
calibrated_unit = CalibratedUnit(unit, calibrated_stage, microscope, camera=camera)
