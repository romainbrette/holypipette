import time

import numpy as np
from numpy import array
import cv2

from .base import TaskController
from setup_script import *
from holypipette.vision.paramecium_tracking import*

class AutopatchError(Exception):
    def __init__(self, message = 'Automatic patching error'):
        self.message = message

    def __str__(self):
        return self.message

class AutoPatcher(TaskController):
    def __init__(self, amplifier, pressure, calibrated_unit, microscope, config):
        super(AutoPatcher, self).__init__()
        self.config = config
        self.amplifier = amplifier
        self.pressure = pressure
        self.calibrated_unit = calibrated_unit
        self.microscope = microscope
        self.cleaning_bath_position = None
        self.rinsing_bath_position = None
        self.paramecium_tank_position =  None

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
                self.calibrated_unit.safe_move(np.array([move_position[0], move_position[1],self.microscope.position()]) + self.microscope.up_direction * np.array([0, 0, 1.]) * self.config.cell_distance, recalibrate=True)
                self.calibrated_unit.wait_until_still()

                # Wait for a few seconds

            # Check initial resistance
            self.amplifier.auto_pipette_offset()
            self.sleep(4.)
            R = self.amplifier.resistance()
            self.debug("Resistance:" + str(R/1e6))
            if R < self.config.min_R:
                raise AutopatchError("Resistance is too low (broken tip?)")
            elif R > self.config.max_R:
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

    def clean_pipette(self):
        if self.cleaning_bath_position is None:
            raise ValueError('Cleaning bath position has not been set')
        if self.rinsing_bath_position is None:
            raise ValueError('Rinsing bath position has not been set')
        try:
            start_position = self.calibrated_unit.position()
            # Move the pipette to the washing bath.
            self.calibrated_unit.absolute_move(self.cleaning_bath_position[0], 0)
            self.calibrated_unit.wait_until_still(0)
            self.calibrated_unit.absolute_move(self.cleaning_bath_position[2] - 5000, 2)
            self.calibrated_unit.wait_until_still(2)
            self.calibrated_unit.absolute_move(self.cleaning_bath_position[1], 1)
            self.calibrated_unit.wait_until_still(1)
            self.calibrated_unit.absolute_move(self.cleaning_bath_position[2], 2)
            self.calibrated_unit.wait_until_still(2)
            # Fill up with the Alconox
            self.pressure.set_pressure(-600)
            self.sleep(1)
            # 5 cycles of tip cleaning
            for i in range(1, 5):
                self.pressure.set_pressure(-600)
                self.sleep(0.625)
                self.pressure.set_pressure(1000)
                self.sleep(0.375)

            # Step 2: Rinsing.
            # Move the pipette to the rinsing bath.
            self.calibrated_unit.absolute_move(self.rinsing_bath_position[2] - 5000, 2)
            self.calibrated_unit.wait_until_still(2)
            self.calibrated_unit.absolute_move(self.rinsing_bath_position[1], 1)
            self.calibrated_unit.wait_until_still(1)
            self.calibrated_unit.absolute_move(self.rinsing_bath_position[0], 0)
            self.calibrated_unit.wait_until_still(0)
            self.calibrated_unit.absolute_move(self.rinsing_bath_position[2], 2)
            self.calibrated_unit.wait_until_still(2)
            # Expel the remaining Alconox
            self.pressure.set_pressure(1000)
            self.sleep(6)

            # Step 3: Move back.
            self.calibrated_unit.absolute_move(0, 0)
            self.calibrated_unit.wait_until_still(0)
            self.calibrated_unit.absolute_move(start_position[1], 1)
            self.calibrated_unit.wait_until_still(1)
            self.calibrated_unit.absolute_move(start_position[2], 2)
            self.calibrated_unit.wait_until_still(2)
            self.calibrated_unit.absolute_move(start_position[0], 0)
            self.calibrated_unit.wait_until_still(0)
        finally:
            self.pressure.set_pressure(self.config.pressure_near)

    def sequential_patching(self):
        from holypipette.gui import movingList
        if self.cleaning_bath_position is None:
            raise ValueError('Cleaning bath position has not been set')
        if self.rinsing_bath_position is None:
            raise ValueError('Rinsing bath position has not been set')
        try:
            length = len(movingList.moveList)
            for iteration in range (length):
                self.amplifier.start_patch()
                # Pressure level 1
                self.pressure.set_pressure(self.config.pressure_near)
                # Move pipette to target
                move_position = movingList.moveList[iteration]
                currentPosition = move_position
                self.calibrated_unit.safe_move(np.array([move_position[0], move_position[1],self.microscope.position()]) + self.microscope.up_direction * np.array([0, 0, 1.]) * self.config.cell_distance, recalibrate=True)
                self.calibrated_unit.wait_until_still()
                self.amplifier.auto_pipette_offset()
                self.sleep(4.)
                R = self.amplifier.resistance()
                self.debug("Resistance:" + str(R / 1e6))
                if R < self.config.min_R:
                    raise AutopatchError("Resistance is too low (broken tip?)")
                elif R > self.config.max_R:
                    raise AutopatchError("Resistance is too high (obstructed?)")

                # Check resistance again
                # oldR = R
                # R = self.amplifier.resistance()
                # if abs(R - oldR) > self.config.max_R_increase:
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
                    try:
                        move_position = movingList.moveList[iteration]
                    except:
                        move_position = currentPosition

                    # sum of variation in both x and y > 5 pixel --> compensation
                    if (len(move_position)>0) & (abs(currentPosition.flatten().sum() - move_position.flatten().sum()) > 5):
                        currentPosition = move_position
                        self.calibrated_unit.safe_move(np.array([move_position[0], move_position[1],self.microscope.position()]) + self.microscope.up_direction * np.array([0, 0, 1.]) * self.config.cell_distance, recalibrate=True)
                        self.calibrated_unit.wait_until_still()

                    self.sleep(1)
                    R = self.amplifier.resistance()
                    self.info("R = " + str(self.amplifier.resistance() / 1e6))
                    if R > oldR * (1 + self.config.cell_R_increase):  # R increases: near cell?
                        # Release pressure
                        self.info("Releasing pressure")
                        self.pressure.set_pressure(0)
                        self.sleep(10)
                        if R > oldR * (1 + self.config.cell_R_increase):
                            # Still higher, we are near the cell
                            self.debug("Sealing, R = " + str(self.amplifier.resistance() / 1e6))
                            self.pressure.set_pressure(self.config.pressure_sealing)
                            t0 = time.time()
                            t = t0
                            R = self.amplifier.resistance()
                            while (R < self.config.gigaseal_R) | (t - t0 < self.config.seal_min_time):
                                # Wait at least 15s and until we get a Gigaseal
                                t = time.time()
                                if t - t0 < self.config.Vramp_duration:
                                    # Ramp to -70 mV in 10 s (default)
                                    self.amplifier.set_holding(
                                        self.config.Vramp_amplitude * (t - t0) / self.config.Vramp_duration)
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
                self.info("Seal successful, R = " + str(self.amplifier.resistance() / 1e6))
                self.break_in()
                self.amplifier.stop_patch()
                self.pressure.set_pressure(self.config.pressure_near)
                self.clean_pipette()

        finally:
            self.pressure.set_pressure(self.config.pressure_near)

    def microdroplet_making(self):
        if self.paramecium_tank_position is None:
            raise ValueError('Paramecium tank has not been set')
        try:
            self.pressure.set_pressure(0)
            i = 0
            self.calibrated_unit = calibrated_units[1]
            start_position = self.calibrated_unit.position()
            z0 = self.microscope.position()

            self.calibrated_unit = calibrated_units[1]
            # Move the pipette to the paramecium tank.

            self.microscope.absolute_move(0)
            self.microscope.wait_until_still()
            self.calibrated_unit.absolute_move(start_position[0]+15000, 0)
            self.calibrated_unit.wait_until_still(0)
            self.calibrated_unit.absolute_move(start_position[2] - 5000, 2)
            self.calibrated_unit.wait_until_still(2)
            self.calibrated_unit.absolute_move(self.paramecium_tank_position[1], 1)
            self.calibrated_unit.wait_until_still(1)
            self.calibrated_unit.absolute_move(self.paramecium_tank_position[2] - 5000, 2)
            self.calibrated_unit.wait_until_still(2)
            self.calibrated_unit.absolute_move(self.paramecium_tank_position[0], 0)
            self.calibrated_unit.wait_until_still(0)
            self.calibrated_unit.absolute_move(self.paramecium_tank_position[2], 2)
            self.calibrated_unit.wait_until_still(2)

            #Take the liquid. Calculate later
            self.pressure.set_pressure(-self.config.droplet_pressure)
            self.sleep(self.config.droplet_time*self.config.droplet_quantity)
            self.pressure.set_pressure(0)

            #
            # Move back.
            self.calibrated_unit.absolute_move(start_position[0] + 15000, 0)
            self.calibrated_unit.wait_until_still(0)
            self.calibrated_unit.absolute_move(start_position[2]-5000, 2)
            self.calibrated_unit.wait_until_still(2)
            self.calibrated_unit.absolute_move(start_position[1], 1)
            self.calibrated_unit.wait_until_still(1)
            self.calibrated_unit.absolute_move(start_position[2], 2)
            self.calibrated_unit.wait_until_still(2)

            self.calibrated_unit.absolute_move(start_position[0], 0)
            self.calibrated_unit.wait_until_still(0)
            self.microscope.absolute_move(z0)
            self.microscope.wait_until_still()

            self.pressure.set_pressure(self.config.droplet_pressure)
            self.sleep(self.config.droplet_time)

        finally:
            self.pressure.set_pressure(15)

    def paramecium_movement(self):
        from holypipette.gui import movingList
        try:
            movingList.tracking = True
            while movingList.paramecium_stop is False:
                if len(movingList.position_history) > 1:
                    xs = movingList.position_history[-1][0]
                    ys = movingList.position_history[-1][1]
                    #self.calibrated_stage.reference_move(self.calibrated_stage.reference_position() - array([xs, ys, 0]))
                    pass

        finally:
            self.info("Paramecium stopped!")

    def paramecium_catching(self):
        from holypipette.gui import movingList
        try:
            move_position = movingList.position_history[-1]
            self.calibrated_unit.safe_move(np.array([move_position[0], move_position[1], self.microscope.position()]) + self.microscope.up_direction * np.array([0, 0, 1.]) * 10, recalibrate=True)
            while movingList.contact == False:
                self.calibrated_unit.relative_move(1, axis=2)

        finally:
            movingList.paramecium_stop = False
            del movingList.position_history[:]
            movingList.contact = False
            movingList.tracking = False
            movingList.black_area = []

