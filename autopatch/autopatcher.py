'''
Automatic patch-clamp algorithm
'''
import time
from numpy import array

__all__ = ['AutoPatcher']

from parameters import *

class AutoPatcher(object):
    '''
    A class to run automatic patch-clamp
    '''
    def __init__(self, amplifier, patcher, pressure, calibrated_unit, microscope):
        self.amplifier = amplifier
        self.patcher = patcher
        self.pressure = pressure
        self.calibrated_unit = calibrated_unit
        self.microscope = microscope

    def run(self, move_position):  # Start the patch-clamp procedure
        self.patcher.start()
        # Pressure level 1
        self.pressure.set_pressure(param_pressure_near)

        # Wait for a few seconds
        time.sleep(4.)

        # Check initial resistance
        R = self.patcher.resistance()
        print("Resistance:" + str(R))
        if R < param_Rmin:
            print("Resistance is too low (broken tip?)")
            self.patcher.stop()
            return
        elif R > param_Rmax:
            print("Resistance is too high (obstructed?)")
            self.patcher.stop()
            return

        # Move pipette to target
        self.calibrated_unit.safe_move(move_position + self.microscope.up_direction * array([0, 0, 1.]) * param_cell_distance)

        # Check resistance again
        oldR = R
        R = self.patcher.resistance()
        if abs(R - oldR) > param_max_R_increase:
            print("Pipette is obstructed; R = " + str(R))
            self.patcher.stop()
            return

        # Release pressure
        print("Releasing pressure")
        self.pressure.set_pressure(0)

        # Pipette offset
        self.amplifier.auto_pipette_offset()
        time.sleep(2)  # why?

        # Approach and make the seal
        print("Approaching the cell")
        success = False
        for _ in range(param_max_distance):  # move 15 um down
            # move by 1 um down
            # Cleaner: use reference relative move
            self.calibrated_unit.relative_move(1, axis=2)  # *calibrated_unit.up_position[2]
            self.calibrated_unit.wait_until_still(2)
            time.sleep(1)
            oldR = R
            R = self.patcher.resistance()
            print("R = " + str(self.patcher.resistance()))
            if R > oldR * (1 + param_cell_R_increase):  # R increases: near cell?
                time.sleep(10)
                if R > oldR * (1 + param_cell_R_increase):
                    # Still higher, we are near the cell
                    print("Sealing, R = " + str(self.patcher.resistance()))
                    self.pressure.set_pressure(param_pressure_sealing)
                    t0 = time.time()
                    t = t0
                    R = self.patcher.resistance()
                    while (R < param_gigaseal_R) | (t - t0 < param_seal_min_time):
                        # Wait at least 15s and until we get a Gigaseal
                        t = time.time()
                        if t - t0 < param_Vramp_duration:
                            # Ramp to -70 mV in 10 s (default)
                            self.amplifier.set_holding(param_Vramp_amplitude * (t - t0) / param_Vramp_duration)
                        if t - t0 >= param_seal_deadline:
                            # No seal in 90 s
                            print("Seal unsuccessful")
                            self.patcher.stop()
                            return
                        R = self.patcher.resistance()
                    success = True
                    break
        self.pressure.set_pressure(0)
        if not success:
            print("Seal unsuccessful")
            self.patcher.stop()
            return

        print("Seal successful, R = " + str(self.patcher.resistance()))

        # Go whole-cell
        print("Breaking in")
        trials = 0
        R = self.patcher.resistance()
        if R < param_gigaseal_R:
            print("Seal lost")
            self.patcher.stop()
            return

        while self.patcher.resistance() > param_max_cell_R:  # Success when resistance goes below 300 MOhm
            if trials == param_breakin_trials:
                print("Break-in unsuccessful")
                self.patcher.stop()
                return
            if param_zap:
                self.amplifier.zap()
                self.pressure.ramp(amplitude=param_pressure_ramp_amplitude, duration=param_pressure_ramp_duration)
            time.sleep(1.3)
            trials += 1

        print("Successful break-in, R = " + str(self.patcher.resistance()))

        self.patcher.stop()
