'''
Automatic patch-clamp algorithm
'''
import time
import numpy as np

from PyQt5 import QtCore

from base.controller import TaskController
from base.executor import TaskExecutor

__all__ = ['AutoPatchController', 'AutopatchError']

from patch_parameters import *


class AutopatchError(Exception):
    def __init__(self, message = 'Automatic patching error'):
        self.message = message

    def __str__(self):
        return self.message


class AutoPatcher(TaskExecutor):
    def __init__(self, amplifier, pressure, calibrated_unit, microscope):
        super(AutoPatcher, self).__init__()
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
        if R < param_gigaseal_R:
            raise AutopatchError("Seal lost")

        pressure = 0
        trials = 0
        while self.amplifier.resistance() > param_max_cell_R:  # Success when resistance goes below 300 MOhm
            trials+=1
            self.debug('Trial: '+str(trials))
            pressure += param_pressure_ramp_increment
            if abs(pressure) > abs(param_pressure_ramp_max):
                raise AutopatchError("Break-in unsuccessful")
            if param_zap:
                self.debug('zapping')
                self.amplifier.zap()
            self.pressure.ramp(amplitude=pressure, duration=param_pressure_ramp_duration)
            self.sleep(1.3)

        self.info("Successful break-in, R = " + str(self.amplifier.resistance() / 1e6))

    def patch(self, move_position=None):
        '''
        Runs the automatic patch-clamp algorithm, including manipulator movements.
        '''
        try:
            self.amplifier.start_patch()
            # Pressure level 1
            self.pressure.set_pressure(param_pressure_near)

            if move_position is not None:
                # Move pipette to target
                self.calibrated_unit.safe_move(move_position + self.microscope.up_direction * np.array([0, 0, 1.]) * param_cell_distance,
                                               recalibrate=True)
                self.calibrated_unit.wait_until_still()

                # Wait for a few seconds

            # Check initial resistance
            self.amplifier.auto_pipette_offset()
            self.sleep(4.)
            R = self.amplifier.resistance()
            self.debug("Resistance:" + str(R/1e6))
            if R < param_Rmin:
                raise AutopatchError("Resistance is too low (broken tip?)")
            elif R > param_Rmax:
                raise AutopatchError("Resistance is too high (obstructed?)")

            # Check resistance again
            #oldR = R
            #R = self.amplifier.resistance()
            #if abs(R - oldR) > param_max_R_increase:
            #    raise AutopatchError("Pipette is obstructed; R = " + str(R/1e6))

            # Pipette offset
            self.amplifier.auto_pipette_offset()
            self.sleep(2)  # why?

            # Approach and make the seal
            self.info("Approaching the cell")
            success = False
            oldR = R
            for _ in range(param_max_distance):  # move 15 um down
                # move by 1 um down
                # Cleaner: use reference relative move
                self.calibrated_unit.relative_move(1, axis=2)  # *calibrated_unit.up_position[2]
                self.abort_if_requested()
                self.calibrated_unit.wait_until_still(2)
                self.sleep(1)
                R = self.amplifier.resistance()
                self.info("R = " + str(self.amplifier.resistance()/1e6))
                if R > oldR * (1 + param_cell_R_increase):  # R increases: near cell?
                    # Release pressure
                    self.info("Releasing pressure")
                    self.pressure.set_pressure(0)
                    time.sleep(10)
                    if R > oldR * (1 + param_cell_R_increase):
                        # Still higher, we are near the cell
                        self.debug("Sealing, R = " + str(self.amplifier.resistance()/1e6))
                        self.pressure.set_pressure(param_pressure_sealing)
                        t0 = time.time()
                        t = t0
                        R = self.amplifier.resistance()
                        while (R < param_gigaseal_R) | (t - t0 < param_seal_min_time):
                            # Wait at least 15s and until we get a Gigaseal
                            t = time.time()
                            if t - t0 < param_Vramp_duration:
                                # Ramp to -70 mV in 10 s (default)
                                self.amplifier.set_holding(param_Vramp_amplitude * (t - t0) / param_Vramp_duration)
                            if t - t0 >= param_seal_deadline:
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
            self.pressure.set_pressure(param_pressure_near)


class AutoPatchController(TaskController):
    '''
    A class to run automatic patch-clamp
    '''
    def __init__(self, amplifier, pressure, pipette_controller):
        super(AutoPatchController, self).__init__()
        self.amplifier = amplifier
        self.pressure = pressure
        self.pipette_controller = pipette_controller
        self.autopatcher_by_unit = {}
        for idx, calibrated_unit in enumerate(self.pipette_controller.calibrated_units):
            autopatcher = AutoPatcher(amplifier, pressure, calibrated_unit,
                                      calibrated_unit.microscope)
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
