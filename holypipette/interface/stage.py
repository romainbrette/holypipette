# coding=utf-8
import pickle
import os
import yaml
from holypipette.config import Config, NumberWithUnit, Number, Boolean
from PyQt5 import QtCore, QtWidgets
import uuid

import numpy as np
from PyQt5 import QtCore

from holypipette.interface import TaskInterface, command, blocking_command
import time

class StageConfig(Config):
    stack_min_Z = NumberWithUnit(-50, bounds=(-3000, 0), doc='Minimum Z', unit='µm')
    stack_max_Z = NumberWithUnit(50, bounds=(0, 3000), doc='Maximum Z', unit='µm')
    stack_dZ = NumberWithUnit(5, bounds=(0, 500), doc='Z increment', unit='µm')

    categories = [('Stack', ['stack_min_Z', 'stack_max_Z', 'stack_dZ'])]

class StageInterface(TaskInterface):
    '''
    Controller for the stage and microscope, uncalibrated.
    '''

    manipulator_switched = QtCore.pyqtSignal('QString', 'QString')

    def __init__(self, stage, microscope, camera,
                 config_filename=None):
        super(StageInterface, self).__init__()

        self.config = StageConfig(name='Automated microscope')

        self.microscope = microscope
        self.camera = camera
        self.stage = stage

        self.timer_t0 = time.time()
        self.last_stack_directory = os.path.expanduser('~/holypipette/')

    @command(category='Microscope',
             description='Move microscope by {:.0f}μm',
             default_arg=10)
    def move_microscope(self, distance):
        self.microscope.relative_move(distance)

    @command(category='Microscope',
             description='Set the position of the floor (cover slip)',
             success_message='Cover slip position stored')
    def set_floor(self):
        self.microscope.floor_Z = self.microscope.position()

    @command(category='Stage',
             description='Move stage vertically by {:.0f}μm',
             default_arg=10)
    def move_stage_vertical(self, distance):
        self.stage.relative_move(distance, axis=1)

    @command(category='Stage',
             description='Move stage horizontally by {:.0f}μm',
             default_arg=10)
    def move_stage_horizontal(self, distance):
        self.stage.relative_move(distance, axis=0)

    @blocking_command(category='Microscope',
                      description='Go to the floor (cover slip)',
                      task_description='Go to the floor (cover slip)')
    def go_to_floor(self):
        self.execute(self.microscope.reference_move,
                     argument=0)

    @command(category='Manipulators',
                     description='Reset timer')
    def reset_timer(self):
        self.timer_t0 = time.time()

    # should be blocking, but it's more complicated
    @command(category='Microscope',
                      description='Stack of photos')
    def take_stack(self):
        position = self.microscope.position()
        z = position + np.array(range(int(self.config.stack_min_Z), int(self.config.stack_max_Z), int(self.config.stack_dZ)), dtype=int)

        # Start rather with the last choice
        directory = QtWidgets.QFileDialog.getExistingDirectory(caption='Save stack', directory = self.last_stack_directory,
                                                           options=QtWidgets.QFileDialog.ShowDirsOnly)
        if len(directory):
            self.last_stack_directory = directory

            path = os.path.join(directory, 'stack_'+str(uuid.uuid1())+'_{}.tiff')
            self.microscope.stack(self.camera, z, save=path)
