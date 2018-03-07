# coding=utf-8
'''
Control of automatic patch clamp algorithm
'''
import numpy as np

import param

from holypipette.controller import TaskController
from holypipette.executor import AutoPatcher, AutopatchError

__all__ = ['AutoPatchController', 'PatchConfig']


class NumberWithUnit(param.Number):
    __slots__ = ['unit', 'magnitude']

    def __init__(self, default, unit, magnitude=1.0, *args, **kwds):
        super(NumberWithUnit, self).__init__(default=default, *args, **kwds)
        self.unit = unit
        self.magnitude = magnitude


class PatchConfig(param.Parameterized):
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
    cell_R_increase = param.Number(.15, bounds=(0, 1), doc='Proportional increase in resistance indicating cell presence')
    gigaseal_R = NumberWithUnit(1000e6, bounds=(100e6, 10000e6), doc='Gigaseal resistance', unit='MΩ', magnitude=1e6)

    seal_min_time = NumberWithUnit(15, bounds=(0, 60), doc='Minimum time for seal', unit='s')
    seal_deadline = NumberWithUnit(90., bounds=(0, 300), doc='Maximum time for seal formation', unit='s')

    Vramp_duration = NumberWithUnit(10., bounds=(0, 60), doc='Voltage ramp duration', unit='s')
    Vramp_amplitude = NumberWithUnit(-70e-3, bounds=(-200e-3, 0), doc='Voltage ramp amplitude', unit='mV', magnitude=1e-3)

    zap = param.Boolean(False, doc='Zap the cell to break the seal')

    categories = [('Pressure', ['pressure_near', 'pressure_sealing',
                                'pressure_ramp_increment', 'pressure_ramp_max',
                                'pressure_ramp_duration']),
                  ('Resistance', ['min_R', 'max_R', 'max_R_increase',
                                  'cell_R_increase', 'max_cell_R',
                                  'gigaseal_R']),
                  ('Distance', ['cell_distance', 'max_distance']),
                  ('Seal', ['seal_min_time', 'seal_deadline', 'zap']),
                  ('Voltage ramp', ['Vramp_duration', 'Vramp_amplitude'])]


class AutoPatchController(TaskController):
    '''
    A class to run automatic patch-clamp
    '''
    def __init__(self, amplifier, pressure, pipette_controller):
        super(AutoPatchController, self).__init__()
        self.config = PatchConfig(name='Patch configuration')
        self.amplifier = amplifier
        self.pressure = pressure
        self.pipette_controller = pipette_controller
        self.autopatcher_by_unit = {}
        for idx, calibrated_unit in enumerate(self.pipette_controller.calibrated_units):
            autopatcher = AutoPatcher(amplifier, pressure, calibrated_unit,
                                      calibrated_unit.microscope,
                                      config=self.config)
            self.autopatcher_by_unit[idx] = autopatcher
            self.executors.add(autopatcher)
        # Define commands
        self.add_command('break_in', 'Patch', 'Break into the cell',
                         task_description='Breaking into cell')
        self.add_command('patch_with_move', 'Patch',
                         'Move to cell and patch it',
                         task_description='Moving to cell and patching it')
        self.add_command('patch_without_move', 'Patch',
                         'Patch cell at current position',
                         task_description='Patching cell')

    def handle_blocking_command(self, command, argument):
        if self.amplifier is None or self.pressure is None:
            raise AutopatchError('Need access to amplifier and pressure controller')

        autopatcher = self.autopatcher_by_unit[self.pipette_controller.current_unit]
        if command == 'break_in':
            self.execute(autopatcher, 'break_in')
        elif command == 'patch_with_move':
            self.execute(autopatcher, 'patch', np.array(argument))
        elif command == 'patch_without_move':
            self.execute(autopatcher, 'patch')
        else:
            raise ValueError('Unknown command: %s' % command)

