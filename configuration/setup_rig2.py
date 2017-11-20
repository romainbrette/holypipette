'''
Setup script for the first rig with the LN SM-5
'''
from devices.camera.umanagercamera import Hamamatsu
from devices.manipulator import *

camera = Hamamatsu()
controller = LuigsNeumann_SM5(name='COM3', stepmoves=True)
stage = ManipulatorUnit(controller,[7,8])
microscope = Leica()
calibrated_stage = CalibratedStage(stage, None, microscope, camera=camera)
units = [ManipulatorUnit(controller, [1, 2, 3]), ManipulatorUnit(controller, [4, 5, 6])]
calibrated_units = [CalibratedUnit(units[0], calibrated_stage, microscope, camera=camera),\
                    CalibratedUnit(units[1], calibrated_stage, microscope, camera=camera)]
