User manual
===========

Manipulator selection
---------------------
Select the current manipulator with numbers (1, 2).

Ranges of axes
--------------
To measure the range (minimum and maximum) of the axes of the unit and microscope,
type M, then move the unit axes and microscope Z to all limit positions (min and max
for all axes). This can be done for example by moving to two opposite corners.
The same must be done for all units and for the XY stage. For the XY stage, note that
the calibration process uses the camera and therefore it must be checked that not
only the positions are reachable, but that the image is also acceptable (in particular,
there must be light). Type M again to end the measurement process.

Calibration
-----------

The coordinate systems of the XY stage and manipulators must be matched to the
coordinate system of the camera and microscope. This operation is called
*calibration*. The way it works is by matching photos of the pipette tip.
Thus, it is very important that the image is clean and sharp at all positions
reached by the calibration procedure.

1. Mount a pipette on the manipulator. In principle, any object could be used,
   the main requirement being that it should be sharp and with a good contrast when seen
   under the microscope.

2. Put water on the coverslip, as much as possible.

3. Move the microscope as high as possible. If it is an immersion objective,
   move it up as much as possible while remaining immersed.
   If it is not an immersion objective, focus on the top of the water drop.

4. Move the pipette manually with the tip in focus, in the center of field.

5. Run the calibration (key: C). The program will first move the XY stage,
   then move each axis of the unit. If the unit is mounted on the stage,
   it will also make compensatory movements with the stage when the unit is
   moved beyond the field of view.

The calibration runs a maximum number of ``calibration_moves`` exponential moves,
which consist in a sequence of movements of the axis, each movement being twice
larger than the previous one, with a minimum distance equal to half
``stack_depth``.
The program also stops if the next movement would not be reachable by the axes,
or if it would go beyond the minimum vertical position (Z).
The minimum vertical position for the microscope or *floor* can be set with
key F. It has not been set, then the program chooses 300 um below the current position.
Initially, minimum and maximum ranges of axes are not set, which means that all
positions are considered reachable.

Save the calibration with Ctrl+S.

Secondary calibration
---------------------

When the pipette is changed, or if the pipette appears to be miscalibrated, for
example after a large movement, then the pipette should be recalibrated. The idea
is that the axis angles should be stable but there can be a shift (translation) in
the coordinate systems. To recalibrate, move the pipette in focus and right click
on the tip.
