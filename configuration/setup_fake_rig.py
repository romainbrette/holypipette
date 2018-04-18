'''
"Fake setup" for GUI development on a computer without access to a rig
'''
from holypipette.devices.pressurecontroller import FakePressureController
from holypipette.devices.camera.camera import FakeCamera
from holypipette.devices.manipulator import *

controller = FakeManipulator(min=[-4096, -4096, -1000, -4096, -4096, -1000, -4096, -4096, -1000],
                             max=[4096, 4096, 1000, 4096, 4096, 1000, 4096, 4096, 1000])
controller.x[:3] = [-50, 10, 500]
controller.x[3:6] = [100, -25, 500]
controller.x[8] = 520
camera = FakeCamera(manipulator=controller, image_z=0)
stage = ManipulatorUnit(controller, [7, 8])
microscope = Microscope(controller, 9)
microscope.floor_Z = 0
microscope.up_direction = 1.0
units = [ManipulatorUnit(controller, [1, 2, 3]), ManipulatorUnit(controller, [4, 5, 6])]
amplifier = object()  # Dummy object
pressure = FakePressureController()
