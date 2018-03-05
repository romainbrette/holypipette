# coding=utf-8
'''
Automatic patch-clamp algorithm
'''
import time
import numpy as np

import param

from base.controller import TaskController
from base.executor import TaskExecutor

__all__ = ['AutoPatchController', 'AutopatchError', 'PatchConfig']

class AutopatchError(Exception):
    def __init__(self, message = 'Automatic patching error'):
        self.message = message

    def __str__(self):
        return self.message

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


class AutoPatcher(TaskExecutor):
    def __init__(self, amplifier, pressure, calibrated_unit, microscope, config):
        super(AutoPatcher, self).__init__()
        self.config = config
        self.amplifier = amplifier
        self.pressure = pressure
        self.calibrated_unit = calibrated_unit
        self.microscope = microscope

    def break_in(self):
        '''
        Breaks in. The pipette must be in cell-attached mode
        '''
        self.info("Breaking in")

        R = self.amplifier.resistance()
        if R < self.config.gigaseal_R:
            raise AutopatchError("Seal lost")

        pressure = 0
        trials = 0
        while self.amplifier.resistance() > self.config.max_cell_R:  # Success when resistance goes below 300 MOhm
            trials+=1
            self.debug('Trial: '+str(trials))
            pressure += self.config.pressure_ramp_increment
            if abs(pressure) > abs(self.config.pressure_ramp_max):
                raise AutopatchError("Break-in unsuccessful")
            if self.config.zap:
                self.debug('zapping')
                self.amplifier.zap()
            self.pressure.ramp(amplitude=pressure, duration=self.config.pressure_ramp_duration)
            self.sleep(1.3)

        self.info("Successful break-in, R = " + str(self.amplifier.resistance() / 1e6))

    def patch(self, move_position=None):
        '''
        Runs the automatic patch-clamp algorithm, including manipulator movements.
        '''
        try:
            self.amplifier.start_patch()
            # Pressure level 1
            self.pressure.set_pressure(self.config.pressure_near)

            if move_position is not None:
                # Move pipette to target
                self.calibrated_unit.safe_move(move_position + self.microscope.up_direction * np.array([0, 0, 1.]) * self.config.cell_distance,
                                               recalibrate=True)
                self.calibrated_unit.wait_until_still()

                # Wait for a few seconds

            # Check initial resistance
            self.amplifier.auto_pipette_offset()
            self.sleep(4.)
            R = self.amplifier.resistance()
            self.debug("Resistance:" + str(R/1e6))
            if R < self.config.Rmin:
                raise AutopatchError("Resistance is too low (broken tip?)")
            elif R > self.config.Rmax:
                raise AutopatchError("Resistance is too high (obstructed?)")

            # Check resistance again
            #oldR = R
            #R = self.amplifier.resistance()
            #if abs(R - oldR) > self.config.max_R_increase:
            #    raise AutopatchError("Pipette is obstructed; R = " + str(R/1e6))

            # Pipette offset
            self.amplifier.auto_pipette_offset()
            self.sleep(2)  # why?

            # Approach and make the seal
            self.info("Approaching the cell")
            success = False
            oldR = R
            for _ in range(self.config.max_distance):  # move 15 um down
                # move by 1 um down
                # Cleaner: use reference relative move
                self.calibrated_unit.relative_move(1, axis=2)  # *calibrated_unit.up_position[2]
                self.abort_if_requested()
                self.calibrated_unit.wait_until_still(2)
                self.sleep(1)
                R = self.amplifier.resistance()
                self.info("R = " + str(self.amplifier.resistance()/1e6))
                if R > oldR * (1 + self.config.cell_R_increase):  # R increases: near cell?
                    # Release pressure
                    self.info("Releasing pressure")
                    self.pressure.set_pressure(0)
                    self.sleep(10)
                    if R > oldR * (1 + self.config.cell_R_increase):
                        # Still higher, we are near the cell
                        self.debug("Sealing, R = " + str(self.amplifier.resistance()/1e6))
                        self.pressure.set_pressure(self.config.pressure_sealing)
                        t0 = time.time()
                        t = t0
                        R = self.amplifier.resistance()
                        while (R < self.config.gigaseal_R) | (t - t0 < self.config.seal_min_time):
                            # Wait at least 15s and until we get a Gigaseal
                            t = time.time()
                            if t - t0 < self.config.Vramp_duration:
                                # Ramp to -70 mV in 10 s (default)
                                self.amplifier.set_holding(self.config.Vramp_amplitude * (t - t0) / self.config.Vramp_duration)
                            if t - t0 >= self.config.seal_deadline:
                                # No seal in 90 s
                                self.amplifier.stop_patch()
                                raise AutopatchError("Seal unsuccessful")
                            R = self.amplifier.resistance()
                        success = True
                        break
            self.pressure.set_pressure(0)
            if not success:
                raise AutopatchError("Seal unsuccessful")

            self.info("Seal successful, R = " + str(self.amplifier.resistance()/1e6))

            # Go whole-cell
            self.break_in()

        finally:
            self.amplifier.stop_patch()
            self.pressure.set_pressure(self.config.pressure_near)


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

    def handle_command(self, command, argument):
        if self.amplifier is None or self.pressure is None:
            raise AutopatchError('Need access to amplifier and pressure controller')

        autopatcher = self.autopatcher_by_unit[self.pipette_controller.current_unit]
        if command == 'break_in':
            autopatcher.break_in()
        elif command == 'patch_with_move':
            autopatcher.patch(np.array(argument))
        elif command == 'patch_without_move':
            autopatcher.patch()
        else:
            raise ValueError('Unknown command: %s' % command)
