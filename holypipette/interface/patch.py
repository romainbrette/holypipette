# coding=utf-8
'''
Control of automatic patch clamp algorithm
'''
import numpy as np

from holypipette.config import Config, NumberWithUnit, Number, Boolean
from holypipette.interface import TaskInterface, command, blocking_command
from holypipette.controller import AutoPatcher


__all__ = ['AutoPatchInterface', 'PatchConfig']


class PatchConfig(Config):
    # Note that the hardware uses mbar and um to measure pressure/distances,
    # therefore pressure and distance values are not defined with magnitude 1e-3
    # or 1e-6

    # Pressure parameters
    pressure_near = NumberWithUnit(20, bounds=(0, 100), doc='Pressure during approach', unit='mbar')
    pressure_sealing = NumberWithUnit(-20, bounds=(-100, 0), doc='Pressure for sealing', unit='mbar')
    pressure_ramp_increment = NumberWithUnit(-25, bounds=(-100, 0), doc='Pressure ramp increment', unit='mbar')
    pressure_ramp_max = NumberWithUnit(-300., bounds=(-1000, 0), doc='Pressure ramp maximum', unit='mbar')
    pressure_ramp_duration = NumberWithUnit(1.15, bounds=(0, 10), doc='Pressure ramp duration', unit='s')

    # Normal resistance range
    min_R = NumberWithUnit(2e6, bounds=(0, 1000e6), doc='Minimum normal resistance', unit='MΩ', magnitude=1e6)
    max_R = NumberWithUnit(25e6, bounds=(0, 1000e6), doc='Maximum normal resistance', unit='MΩ', magnitude=1e6)
    max_cell_R = NumberWithUnit(300e6, bounds=(0, 1000e6), doc='Maximum cell resistance', unit='MΩ', magnitude=1e6)
    cell_distance = NumberWithUnit(10, bounds=(0, 100), doc='Initial distance above the target cell', unit='μm')
    max_distance = NumberWithUnit(20, bounds=(0, 100), doc='Maximum length of movement during approach', unit='μm')

    max_R_increase = NumberWithUnit(1e6, bounds=(0, 100e6), doc='Increase in resistance indicating obstruction', unit='MΩ', magnitude=1e6)
    cell_R_increase = Number(.15, bounds=(0, 1), doc='Proportional increase in resistance indicating cell presence')
    gigaseal_R = NumberWithUnit(1000e6, bounds=(100e6, 10000e6), doc='Gigaseal resistance', unit='MΩ', magnitude=1e6)

    seal_min_time = NumberWithUnit(15, bounds=(0, 60), doc='Minimum time for seal', unit='s')
    seal_deadline = NumberWithUnit(90., bounds=(0, 300), doc='Maximum time for seal formation', unit='s')

    Vramp_duration = NumberWithUnit(10., bounds=(0, 60), doc='Voltage ramp duration', unit='s')
    Vramp_amplitude = NumberWithUnit(-70e-3, bounds=(-200e-3, 0), doc='Voltage ramp amplitude', unit='mV', magnitude=1e-3)

    zap = Boolean(False, doc='Zap the cell to break the seal')

    droplet_quantity = Number(1, bounds=(1, 100), doc='Number of microdroplet to make')
    droplet_pressure = NumberWithUnit(15, bounds=(-1000, 1000), doc='Pressure to make droplet', unit='mbar')
    droplet_time = NumberWithUnit(5, bounds=(0, 100), doc='Necessary time to make one droplet', unit='s')


    categories = [('Pressure', ['pressure_near', 'pressure_sealing',
                                'pressure_ramp_increment', 'pressure_ramp_max',
                                'pressure_ramp_duration']),
                  ('Resistance', ['min_R', 'max_R', 'max_R_increase',
                                  'cell_R_increase', 'max_cell_R',
                                  'gigaseal_R']),
                  ('Distance', ['cell_distance', 'max_distance']),
                  ('Seal', ['seal_min_time', 'seal_deadline', 'zap']),
                  ('Voltage ramp', ['Vramp_duration', 'Vramp_amplitude']),
                  ('Paramecium', ['droplet_quantity', 'droplet_pressure','droplet_time'])]


class AutoPatchInterface(TaskInterface):
    '''
    A class to run automatic patch-clamp
    '''
    def __init__(self, amplifier, pressure, pipette_interface):
        super(AutoPatchInterface, self).__init__()
        self.config = PatchConfig(name='Patch config')
        self.amplifier = amplifier
        self.pressure = pressure
        self.pipette_controller = pipette_interface
        self.autopatcher_by_unit = {}
        for idx, calibrated_unit in enumerate(self.pipette_controller.calibrated_units):
            autopatcher = AutoPatcher(amplifier, pressure, calibrated_unit, calibrated_unit.microscope, calibrated_stage= self.pipette_controller.calibrated_stage, config=self.config)
            self.autopatcher_by_unit[idx] = autopatcher
            self.controllers.add(autopatcher)

    @property
    def current_autopatcher(self):
        return self.autopatcher_by_unit[self.pipette_controller.current_unit]

    @blocking_command(category='Patch', description='Break into the cell',
                      task_description='Breaking into the cell')
    def break_in(self):
        self.execute(self.current_autopatcher, 'break_in')

    @blocking_command(category='Patch', description='Move to cell and patch it',
                      task_description='Moving to cell and patching it')
    def patch_with_move(self, position):
        self.execute(self.current_autopatcher, 'patch', np.array(position))

    @blocking_command(category='Patch',
                      description='Patch cell at current position',
                      task_description='Patching cell')
    def patch_without_move(self, position=None):
        # If this command is linked to a mouse click, it will receive the
        # position as an argument -- we simply ignore it
        self.execute(self.current_autopatcher, 'patch')

    @command(category='Patch',
             description='Store the position of the washing bath')
    def store_cleaning_position(self):
        self.current_autopatcher.cleaning_bath_position = self.pipette_controller.calibrated_unit.position()
        self.info('Cleaning bath position stored')

    @command(category='Patch',
             description='Store the position of the rinsing bath')
    def store_rinsing_position(self):
        self.current_autopatcher.rinsing_bath_position = self.pipette_controller.calibrated_unit.position()
        self.info('Rinsing bath position stored')

    @command(category='Patch',
             description='Store the position of the paramecium tank')
    def store_paramecium_position(self):
        self.current_autopatcher.paramecium_tank_position = self.pipette_controller.calibrated_units[1].position()
        self.info('Paramecium tank position stored')

    @blocking_command(category='Patch',
                      description='Clean the pipette (wash and rinse)',
                      task_description='Cleaning the pipette')
    def clean_pipette(self):
        self.execute(self.current_autopatcher, 'clean_pipette')

    @blocking_command(category='Patch',
                      description='Sequential patching and cleaning for multiple cells',
                      task_description='Sequential patch clamping')
    def sequential_patching(self):
        self.execute(self.current_autopatcher, 'sequential_patching')

    @blocking_command(category='Patch',
                      description='Microdroplet making for paramecium patch clamp',
                      task_description='Microdroplet making')
    def microdroplet_making(self):
        self.execute(self.current_autopatcher, 'microdroplet_making')

    @blocking_command(category='Patch',
                      description='Calibrated stage moving to compensate the movement of paramecium',
                      task_description='Paramecium tracking')
    def paramecium_movement(self):
        self.execute(self.current_autopatcher, 'paramecium_movement')

    @blocking_command(category='Patch',
                      description='Moving down the calibrated manipulator to hold the paramecium',
                      task_description='Paramecium immobilization')
    def paramecium_catching(self):
        self.execute(self.current_autopatcher, 'paramecium_catching')

    @blocking_command(category='Patch',
                      description='Moving down the calibrated manipulator to detect the contact point with the coverslip',
                      task_description='Contact detection')
    def contact_detection(self):
        self.execute(self.current_autopatcher, 'contact_detection')