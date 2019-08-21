'''
Proposed setup script for the first rig at ISIR: Dino Lite USB Microscope, Sensapex Micromanipulator
!Anticirus software need to be turned off to work with microscope and micromanipulator.
!Reset Ethernet link local in Sensapex Suite before running
'''

from holypipette.devices.camera.opencvcamera import OpenCVCamera
from holypipette.devices.manipulator import *
from holypipette.devices.amplifier.amplifier import FakeAmplifier
from holypipette.devices.pressurecontroller import OB1
import traceback

camera = OpenCVCamera()
controller = UMP.get_ump()
stage = ManipulatorUnit(controller, [4, 5])
microscope = Microscope(controller, 6)
calibrated_stage = CalibratedStage(stage, None, microscope, camera=camera)
units = [ManipulatorUnit(controller, [1, 2, 3])]
calibrated_units = [CalibratedUnit(units[0], calibrated_stage, microscope, camera=camera)]
amplifier, pressure = None, None

try:
    amplifier = FakeAmplifier()
    pressure = OB1()
    pressure.set_pressure(25)
except Exception:
    print(traceback.format_exc())