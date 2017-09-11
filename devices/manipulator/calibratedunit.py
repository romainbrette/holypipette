"""
A class to handle a manipulator unit with coordinates calibrated to the reference system of a camera.
It contains methods to calibrate the unit.
"""
from manipulatorunit import *
from numpy import array, ones, zeros, eye, dot
from numpy.linalg import inv
from ..camera import Camera # actually not necessary to import it (just duck typing)

__all__ = ['CalibratedUnit']


class CalibratedUnit(ManipulatorUnit):
    def __init__(self, unit, stage, microscope):
        '''
        Parameters
        ----------
        unit : ManipulatorUnit for the (XYZ) unit
        stage : ManipulatorUnit for the stage
        microscope: ManipulatorUnit for the microscope (single axis)
        '''
        ManipulatorUnit.__init__(self, unit.dev, unit.axes)
        self.stage = stage
        self.microscope = microscope

        # Matrices for passing to the camera/microscope system
        self.Mu = eye(3) # unit to camera; I am assuming a 3 axes unit
        self.Minv = eye(3) # Inverse of M
        self.Ms = array((3,len(stage.axes))) # stage to camera
        self.y0 = zeros(3) # Offset in camera system

    def virtual_position(self): # maybe not a good name?
        '''
        Position in the camera system.

        Returns
        -------
        The current position in um as an XYZ vector.
        '''
        xu = self.position()
        xs = self.stage.position()
        return dot(self.Mu, xu) + dot(self.Ms, xs) + self.y0

    def virtual_move(self, y):
        '''
        Moves the unit to position y in camera system.

        Parameters
        ----------
        y : XYZ position vector in um
        '''
        xs = self.stage.position()
        xu = dot(self.Minv, y-dot(self.Ms, xs)-self.y0)
        self.absolute_move(xu)

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
        self.virtual_move(y + alpha * u)
        # We need to wait here!
        self.wait_until_still()
        # Final move
        self.virtual_move(y - withdraw * u) # Or relative move in manipulator coordinates, first axis (faster)
