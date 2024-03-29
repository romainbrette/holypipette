'''
Setup script for the first rig with the LN SM-10 and one Sensapex
'''
from holypipette.devices.camera.umanagercamera import Lumenera
from holypipette.devices.manipulator import *
from holypipette.devices.amplifier import MultiClampChannel
from holypipette.devices.pressurecontroller import OB1
import traceback # Do we need this?

camera = Lumenera()
controller = LuigsNeumann_SM10(stepmoves=False)
controller_sensapex = UMP.get_ump() # what a name...
stage = ManipulatorUnit(controller, [7, 8])
microscope = Microscope(controller, 9)
calibrated_stage = CalibratedStage(stage, None, microscope, camera=camera)
units = [ManipulatorUnit(controller, [1, 2, 3]), ManipulatorUnit(controller, [4, 5, 6]),
         ManipulatorUnit(controller_sensapex, [0, 1, 2])]
calibrated_units = [CalibratedUnit(units[0], calibrated_stage, microscope, camera=camera),
                    CalibratedUnit(units[1], calibrated_stage, microscope, camera=camera),
                    CalibratedUnit(units[2], calibrated_stage, microscope, camera=camera)]
amplifier, pressure = None, None

try:
    amplifier = MultiClampChannel()
    pressure = OB1()
    pressure.set_pressure(25)
except Exception:
    print(traceback.format_exc()) # What is this?
