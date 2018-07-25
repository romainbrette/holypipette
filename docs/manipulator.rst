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
Calibrated units are manipulator units that can be moved in the coordinate system of the camera.
A ``CalibratedUnit`` must be associated to a camera, a microscope Z axis, and can be attached to an XY stage.
A ``CalibratedStage`` is a special kind that a horizontal XY stage (i.e., to be parallel to the focal plane of the
microscope).
Examples::

    calibrated_stage = CalibratedStage(stage, microscope=microscope, camera=camera)
    XYZ = CalibratedUnit(unit, calibrated_stage, microscope, camera=camera)

The position in the camera system is given by


Calibration algorithms
----------------------
