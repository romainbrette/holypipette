'''
"Fake setup" for GUI development on a computer without access to a rig
'''
from holypipette.devices.camera.camera import FakeCamera
from holypipette.devices.manipulator import *

controller = FakeManipulator(min=[-511, -383, -500, -511, -383, -500, -511, -383, -500],
                             max=[511, 383, 500, 511, 383, 500, 511, 383, 500])
controller.x[:3] = [-150, -50, 200]
controller.x[3:6] = [250, -100, 200]
controller.x[8] = 250
camera = FakeCamera(manipulator=controller)
stage = ManipulatorUnit(controller, [7, 8])
microscope = Microscope(controller, 9)
calibrated_stage = CalibratedStage(stage, None, microscope, camera=camera)
units = [ManipulatorUnit(controller, [1, 2, 3]), ManipulatorUnit(controller, [4, 5, 6])]
calibrated_units = [CalibratedUnit(units[0], calibrated_stage, microscope, camera=camera),\
                    CalibratedUnit(units[1], calibrated_stage, microscope, camera=camera)]
