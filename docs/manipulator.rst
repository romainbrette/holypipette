Manipulators
============

Hardware control
----------------
Manipulators are groups of motorized axes, typically an XY stage or an XYZ unit.
The basic class is a ``ManipulatorUnit``, which depends on a controller. The controller is
a set of axes that can be moved independently (for example the Luigs and Neumann controller, which
controls up to 9 axes).
Example::

    controller = LuigsNeumann_SM10()
    stage = ManipulatorUnit(controller, [7, 8])

A ``ManipulatorUnit`` can be moved with relative or absolute displacements expressed in um.

Calibrated units
----------------
Calibrated units are manipulator units that can be moved in the coordinate system of the camera, called
the reference system.
A ``CalibratedUnit`` must be associated to a camera, a microscope Z axis, and can be attached to an XY stage.
A ``CalibratedStage`` is a special kind that a horizontal XY stage (i.e., to be parallel to the focal plane of the
microscope).
Examples::

    calibrated_stage = CalibratedStage(stage, microscope=microscope, camera=camera)
    XYZ = CalibratedUnit(unit, calibrated_stage, microscope, camera=camera)

The position in the camera system is given by :math:`{\bf M}.{\bf u} + {\bf r}_0 + {\bf r}_S`,
where :math:`{\bf u}` is the position of the manipulator axes,
:math:`{\bf r}_S` is the position of the stage in the reference system to which the manipulator
is attached, :math:`{\bf M}` is coordinate change matrix and :math:`{\bf r}_0` is an offset.

Movement algorithms
-------------------

Reference move
^^^^^^^^^^^^^^
The basic move is a ``reference_move``. It simply inverts the matrix relation to find the
target position in the coordinate system of the manipulator coordinates.
However, this is not as simple as it sounds. For some manipulators (including Luigs and Neumann),
the resulting displacement is not necessarily a straight line because each axis has a fixed speed independent
of the movement. This can result in a broken trajectory; first a diagonal move then a move in the remaining
directions. As a result, the pipette could collide with the coverslip or other problems.
To avoid this problem, the method has a ``safe`` option. If True, the method first determines whether the
the third axis, which is assumed to be Z, will be moved up or down (see calibration algorithms).
If it is going up, then this axis is moved first; otherwise it is moved last. This simple algorithm
maximizes the minimum altitude of the trajectory, so as to avoid colliding with the coverslip.

This is only done with absolute moves and not relative moves.

Withdraw
^^^^^^^^
The ``withdraw`` method moves the first axis to its upper endpoint. This presupposes that the two endpoints
have been previously identified.

Focus
^^^^^
The ``focus`` method moves the microscope Z axis so that the tip is in focus. This does not use an autofocus
but rather the calibration system (so the manipulator must be correctly calibrated for this to work).

Save move
^^^^^^^^^
The ``safe_move`` method moves the manipulator to a target point, with a trajectory that aims at minimizing
mechanical interaction with the tissue. It also essentially removes the pipette from the field of view during the
approach, which could be helpful if tracking the cell.

If the movement is up, a normal movement is done (with the ``safe`` option). If it is down, then the trajectory
is more complex. First, the manipulator is moved horizontally, then along the first axis of the manipulator.
Note that by horizontally, it is meant that the start and end positions are on the same horizontal plane, but
the trajectory does not necessarily remain in that plane for reasons explained above; thus the
``safe`` option is also used.

If the ``recalibrate`` option is True and the movement is at least 500 um, then the program tries to fix
errors in calibration before the target. To this end, the manipulator stops 50 um before the target,
then focus on the tip, automatically recalibrate (see below), then move the focus back, and finish the movement.

Moving a new pipette in the field
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This is not fully tested code. The ``move_new_pipette_back`` method moves a new pipette into the field.
This assumes that the calibration is right, except for an offset (due e.g. to the length and slightly different
geometry of the pipette). The algorithm is as follows:

1. Move the pipette 2 mm before target position (in the direction of the first axis),
   which is the center of the microscope view.
2. Take 10 photos at 10 Hz.
3. Calculate the mean standard deviation of the images (more or less the contrast).
4. Move the pipette down by 100 um along the axis.
5. If the standard deviation of the image differs by at least 20% from the mean calculated previously, stop.
6. Otherwise, go to 4; stop at 5 mm.

In practice, if the pipette is cleaned, this method might not be that useful.

Move and track
^^^^^^^^^^^^^^
The ``move_and_track`` is used by calibration algorithms. It moves the pipette along one axis,
then focus the microscope on the tip using calculation and then template matching. Optionally,
it also moves the stage to center the tip. The final image is focused on the tip, but the tip
is not necessarily in the center (depending on the precision of calibration).
Finally, it returns the position of the tip on screen and focal plane.

Move back
^^^^^^^^^
The ``move_back`` method is used by calibration algorithms.
It moves the microscope, manipulator and stage to a given position (previously stored), in
a certain order that is intended to avoid collisions.
First, the microscope is moved (normally, up), then the manipulator, then the stage.
The pipette is then back at the initial position, which is supposed to be in focus in the center
of view. Then the pipette is located and refocused, and the pipette position and focal plane are
returned.

Calibration algorithms
----------------------
Calibration consists in determining the matrix :math:`{\bf M}` and the offset :math:`{\bf r}_0`, as well
as whether the axes go up or down (in Z) in the positive direction.

Recalibration
^^^^^^^^^^^^^
This assumes that the manipulator is correctly calibrated, except for an offset.
The method ``recalibrate`` updates :math:`{\bf r}_0` assuming that the tip is in the center of view
(red cross).

Stage calibration
^^^^^^^^^^^^^^^^^
The stage is assumed to be horizontal, and thus the Z axis of the microscope is not moved.
It is assumed that there is an object in focus in the field of view, attached to the stage
(pipette, or coverslip). Algorithm:

1. Take a photo of the center of the field: this is the template.
2. Move the first axis by 40 um, and locate the template in the image: deduce
   the first column of :math:`{\bf M}`.
3. Repeat for the second axis.
4. Using the first estimate of :math:`{\bf M}`, move to each of three corners of the image
   (top left, top right, bottom left), with a safety margin, and locate the template.
5. Calculate :math:`{\bf M}` again based on these three points.

Manipulator calibration
^^^^^^^^^^^^^^^^^^^^^^^
This is the ``calibrate`` method, plus a number of methods that it calls.
The tip must be in focus at the center of view.

*Initial steps*

1. Calibrate the stage to which it is attached.
2. Take photos of the pipette along the Z axis of the microscope, every 1 um over
   distance ``stack_depth`` (positive and negative).

*First estimate*

1. Move and track the first axis by a distance equal to half the ``stack_depth``.
   As initially the matrix is zero, there is no predictive move of the focus.
2. Repeat for each axis.
3. Calculate the matrix.
4. Go back to the initial position.

This first very crude estimate is used to calculate the vertical direction of the axes.

*Up directions*

This is done in method ``calculate_up_directions``. It takes the matrix and estimates
for each axis whether a positive movement makes the pipette go up or down.
Then the minimum reachable Z (coverslip) is determined as 300 um below the current position,
unless it has been specified explicitly (floor position).

*Calibration*

Manual calibration
^^^^^^^^^^^^^^^^^^

Automatic recalibration
^^^^^^^^^^^^^^^^^^^^^^^
