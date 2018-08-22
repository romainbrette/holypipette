Automatic patch clamp
=====================

These are automatic patch clamp algorithms adapted from the literature.

Main patch clamp algorithm
--------------------------

Amplifier start-up (on Multiclamp 700B):

1. Voltage-clamp.
2. Disable resistance metering and pulses.
3. Compensate pipette (slow and fast).
4. Set pulse amplitude and frequency (default 1e-2 and 1e-2, units unclear).
5. Set zap duration at 1 ms.
6. Do pipette offset (V=0).
7. Set holding potential V = 0.
8. Enable resistance metering (triggers voltage pulses).

Approach:

1. Set pressure at ``pressure_near`` (>0).
2. Move the manipulator with a safe move to a distance ``cell_distance`` above the target position, if specified.
3. Do pipette offset (V=0) and wait for 4 s.
4. Measure resistance R, stop if not within specified bounds.
5. Do pipette offset and wait for 2 s.
6. Move down by 1 µm and wait for 1 s (maximum total movement ``max_distance``).
7. Measure R. Unless R has increased by ``1+cell_R_increase``, repeat (7).

Sealing:

1. Release the pressure and wait for 10 s.
2. If ``1+cell_R_increase``: go back to approach (7). Note that pressure is now released.
3. Set pressure at ``pressure_sealing`` (<0).
4. If ``R>gigaseal_R``: success (next stage).
5. Ramp V down to ``Vramp_amplitude`` (default -70 mV) over duration ``Vramp_duration``.
6. Wait for at least ``seal_min_time``, and until ``R>gigaseal_R`` (success) or time is out (``seal_deadline``) (failure).
7. Success or failure: release pressure.

Break-in:

1. If ``R<gigaseal_R``: failure (seal lost).
2. Increase max pressure by ``pressure_ramp_increment``; fail if greater than ``pressure_ramp_max``.
3. If ``zap`` is True, do an electric zap.
4. Do a pressure ramp up to max pressure, of duration ``pressure_ramp_duration``; wait for 1.3 s.
5. If ``R<max_cell_R``: success.

Ending (also if stopped in the middle):

1. Stop the amplifier: disable resistance metering and pulses; current-clamp.
2. Set the pressure at ``pressure_near`` (>0).
