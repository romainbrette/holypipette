'''
Proposed setup script for the first rig at ISIR: Dino Lite USB Microscope, Sensapex Micromanipulator
!Antivirus software need to be turned off to work with microscope and micromanipulator.
!Reset Ethernet link local in Sensapex Suite before running
'''

from holypipette.devices.camera.opencvcamera import OpenCVCamera
from holypipette.devices.manipulator import *
from holypipette.devices.amplifier.amplifier import FakeAmplifier
from holypipette.devices.pressurecontroller import FakePressureController
from holypipette.devices.camera.camera import FakeCamera
import traceback


camera = OpenCVCamera()
controller1 = UMP.get_ump()
controller2 = Prior()
stage = ManipulatorUnit(controller2, [0, 1])
#microscope = Microscope(controller2, 2)
microscope = Microscope(controller1,2)
calibrated_stage = CalibratedStage(stage, None, microscope, camera=camera)
#units = [ManipulatorUnit(controller1, [0, 1, 2]), ManipulatorUnit(controller1, [3, 4, 5])]
units = [ManipulatorUnit(controller1, [3, 4, 5])]
#calibrated_units = [CalibratedUnit(units[0], calibrated_stage, microscope, camera=camera),\
#                    CalibratedUnit(units[1], calibrated_stage, microscope, camera=camera)]
calibrated_units = [CalibratedUnit(units[0], calibrated_stage, microscope, camera=camera)]
amplifier, pressure = None, None

try:
    amplifier = FakeAmplifier()
    pressure = FakePressureController()
except Exception:
    print(traceback.format_exc())