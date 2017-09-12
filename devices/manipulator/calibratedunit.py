"""
A class to handle a manipulator unit with coordinates calibrated to the reference system of a camera.
It contains methods to calibrate the unit.

Should these run in a thread?
Should messages be issued?
Also ranges should be taken into account
"""
from manipulatorunit import *
from numpy import array, ones, zeros, eye, dot
from numpy.linalg import inv
from ..camera import Camera # actually not necessary to import it (just duck typing)

__all__ = ['CalibratedUnit']

class Objective(object):
    '''
    An objective is defined by a magnification factor (4, 20, 40x),
    an offset for the focal plane, and a conversion factor from um to px
    (which is camera-dependent).
    '''
    def __init__(self, magnification, factor, offset):
        self.magnification = magnification
        self.factor = factor
        self.offset = offset

class CalibratedUnit(ManipulatorUnit):
    def __init__(self, unit, stage, microscope):
        '''
        A manipulator unit calibrated to a fixed reference coordinate system.
        The stage refers to a platform on which the unit is mounted, which can
        be None. The platform must be calibrated too (if it exists).

        Parameters
        ----------
        unit : ManipulatorUnit for the (XYZ) unit
        stage : CalibratedUnit for the stage
        microscope: ManipulatorUnit for the microscope (single axis)
        '''
        ManipulatorUnit.__init__(self, unit.dev, unit.axes)
        if stage is None: # In this case we assume the unit is on a fixed element.
            self.stage = FixedStage()
        else:
            self.stage = stage
        self.microscope = microscope # in fact not useful

        # Matrices for passing to the camera/microscope system
        self.M = array((3,len(unit.axes))) # unit to camera
        self.Minv = array((len(unit.axes),3)) # Inverse of M, when well defined (otherwise pseudoinverse? pinv)
        self.y0 = zeros(3) # Offset in camera system

        # Dictionary of objectives and conditions (immersed/non immersed)
        self.objective = dict()

    def reference_position(self):
        '''
        Position in the reference camera system.

        Returns
        -------
        The current position in um as an XYZ vector.
        '''
        x = self.position()
        return dot(self.M, x) + self.y0 + self.stage.reference_position()

    def reference_move(self, y):
        '''
        Moves the unit to position y in reference camera system, without moving the stage.

        Parameters
        ----------
        y : XYZ position vector in um
        '''
        x = dot(self.Minv, y-self.stage.reference_position()-self.y0)
        self.absolute_move(x)

    def safe_move(self, y, withdraw = 0.):
        '''
        Moves the device to position x (an XYZ vector) in a way that minimizes
        interaction with tissue. The manipulator is first moved horizontally,
        then along the pipette axis.

        Parameters
        ----------
        y : target position in um, an (X,Y,Z) vector
        withdraw : in um; if not 0, the pipette is withdrawn by this value from the target position x
        '''
        # First, we determine the intersection between the line going through x
        # with direction corresponding to the manipulator first axis.
        #n = array([0,0,1.]) # vector normal the focal plane (we are in stage coordinates)
        #u = dot(self.M, array([1.,0.,0.]))
        u = self.M[:,0] # this is the vector for the first manipulator axis
        xprime = self.position()
        #alpha = dot(n,xprime-x)/dot(n,u)
        #alpha = (self.position()-x)[2] / u[2]

        alpha = (xprime - y)[2] / self.M[2,0]
        # TODO: check whether the intermediate move is accessible

        # Intermediate move
        self.reference_move(y + alpha * u)
        # We need to wait here!
        self.wait_until_still()
        # Final move
        self.reference_move(y - withdraw * u) # Or relative move in manipulator coordinates, first axis (faster)

    def calibrate(self, camera, horizontal = False):
        '''
        Automatic calibration of the manipulator using the camera.
        It is assumed that the pipette or some element attached to the unit is in the center of the image.

        Parameters
        ----------
        camera: a camera with a snap() method, returning the current image
        horizontal: if True, the stage is assumed to be parallel to the focal plane (no autofocus)
        '''
        # Simple case (horizontal):
        # 1) Move each axis by a small displacement
        # 2) Compute the matrix from unit to camera (pixels)
        # 3) Move to three corners using the computed matrix
        # 4) Recompute the matrix
        # 5) Calculate conversion factor.
        # 6) Offset is considered null.

        # Complex case (not horizontal, no attached stage):
        # 1) Take a stack of photos on different focal planes
        # 2) Move axis by a small displacement
        # 3) Move focal plane by estimated amount (initially 0)
        # 4) Estimate focal plane and position
        # 5) Estimate matrix column
        # 6) Multiply displacement by 2, and back to 2
        # 7) Stop when predicted move is out of screen
        # 8) Calculate conversion factor and offset.

        # Attached stage and Z axis
        # Same as above except:
        # * move the stage after unit movement to recenter
        # * stop when position is unreachable
        pass

class FixedStage(CalibratedUnit):
    '''
    A stage that cannot move. This is used to simplify the code.
    '''
    def __init__(self):
        self.position = array([0.,0.,0.])

    def reference_position(self):
        return self.position
