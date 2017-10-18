"""
A class to handle a manipulator unit with coordinates calibrated to the reference system of a camera.
It contains methods to calibrate the unit.

Should these run in a thread?
Should messages be issued?
Also ranges should be taken into account

Should this be in devices/*? Maybe in a separate calibration folder
"""
from manipulatorunit import *
from numpy import array, ones, zeros, eye, dot, arange, vstack, sign
from numpy.linalg import inv, pinv, norm
from vision.templatematching import templatematching
from time import sleep
from vision.crop import *
from vision.findpipette import *
import cv2
from time import sleep

__all__ = ['CalibratedUnit','CalibrationError','CalibratedStage']

verbose = True
position_tolerance = 0.1 # in um
sleep_time = 1. # Sleep time before taking pictures after a pipette move, because the pipette might vibrate

class CalibrationError(Exception):
    def __init__(self, message = 'Device is not calibrated'):
        self.message = message

    def __str__(self):
        return self.message


# class Objective(object):
#     '''
#     An objective is defined by a magnification factor (4, 20, 40x),
#     an offset for the focal plane, and a conversion factor from um to px
#     (which is camera-dependent).
#     '''
#     def __init__(self, magnification, factor, offset):
#         self.magnification = magnification
#         self.factor = factor
#         self.offset = offset

class CalibratedUnit(ManipulatorUnit):
    def __init__(self, unit, stage=None, microscope=None, camera = None):
        '''
        A manipulator unit calibrated to a fixed reference coordinate system.
        The stage refers to a platform on which the unit is mounted, which can
        be None.

        Parameters
        ----------
        unit : ManipulatorUnit for the (XYZ) unit
        stage : CalibratedUnit for the stage
        microscope : ManipulatorUnit for the microscope (single axis)
        camera : a camera, ie, object with a snap() method (optional, for visual calibration)
        '''
        ManipulatorUnit.__init__(self, unit.dev, unit.axes)
        if stage is None: # In this case we assume the unit is on a fixed element.
            self.stage = FixedStage()
            self.fixed = True
        else:
            self.stage = stage
            self.fixed = False
        self.microscope = microscope
        self.camera = camera

        self.calibrated = False
        self.up_direction = [-1 for _ in range(len(unit.axes))] # Default up direction, determined during calibration

        # Matrices for passing to the camera/microscope system
        self.M = zeros((3,len(unit.axes))) # unit to camera
        self.Minv = zeros((len(unit.axes),3)) # Inverse of M, when well defined (otherwise pseudoinverse? pinv)
        self.r0 = zeros(3) # Offset in reference system

        # Dictionary of objectives and conditions (immersed/non immersed)
        #self.objective = dict()

    def reference_position(self):
        '''
        Position in the reference camera system.

        Returns
        -------
        The current position in um as an XYZ vector.
        '''
        if not self.calibrated:
            raise CalibrationError
        u = self.position() # position vector in manipulator unit system
        return dot(self.M, u) + self.r0 + self.stage.reference_position()

    def reference_move(self, r):
        '''
        Moves the unit to position r in reference camera system, without moving the stage.

        Parameters
        ----------
        r : XYZ position vector in um
        '''
        if not self.calibrated:
            raise CalibrationError
        u = dot(self.Minv, r-self.stage.reference_position()-self.r0)
        self.absolute_move(u)

    def reference_relative_move(self, r):
        '''
        Moves the unit by vector r in reference camera system, without moving the stage.

        Parameters
        ----------
        r : XYZ position vector in um
        '''
        if not self.calibrated:
            raise CalibrationError
        u = dot(self.Minv, r)
        self.relative_move(u)

    def safe_move(self, r, withdraw = 0.):
        '''
        Moves the device to position x (an XYZ vector) in a way that minimizes
        interaction with tissue. The manipulator is first moved horizontally,
        then along the pipette axis.

        Parameters
        ----------
        r : target position in um, an (X,Y,Z) vector
        withdraw : in um; if not 0, the pipette is withdrawn by this value from the target position x
        '''
        if not self.calibrated:
            raise CalibrationError
        # First, we determine the intersection between the line going through x
        # with direction corresponding to the manipulator first axis.
        #n = array([0,0,1.]) # vector normal the focal plane (we are in stage coordinates)
        #p = dot(self.M, array([1.,0.,0.]))
        p = self.M[:,0] # this is the vector for the first manipulator axis
        uprime = self.position()
        #alpha = dot(n,uprime-u)/dot(n,p)
        #alpha = (self.position()-u)[2] / p[2]

        alpha = (uprime - r)[2] / self.M[2,0]
        # TODO: check whether the intermediate move is accessible

        # Intermediate move
        self.reference_move(r + alpha * p)
        # We need to wait here!
        self.wait_until_still()
        # Final move
        self.reference_move(r - withdraw * p) # Or relative move in manipulator coordinates, first axis (faster)

    def calibrate(self, message = lambda str: None):
        '''
        Automatic calibration of the manipulator using the camera.
        It is assumed that the pipette or some element attached to the unit is in the center of the image.

        Parameters
        ----------
        message : a function to which messages are passed
        '''
        if not self.stage.calibrated:
            self.stage.calibrate(message=message)

        if self.fixed:
            self.calibrate_without_stage(message)
        else:
            self.calibrate_with_stage(message)

    def calibrate_without_stage(self, message = lambda str: None):
        '''
        Automatic calibration of the manipulator using the camera.
        It is assumed that the pipette or some element attached to the unit is in the center of the image.
        The stage is fixed.

        Parameters
        ----------
        message : a function to which messages are passed
        '''
        # 0) Determine pipette cardinal position (N, S, E, W etc)
        pipette_position = pipette_cardinal(crop_center(self.camera.snap()))
        message("Pipette cardinal position: "+str(pipette_position))

        # 1) Take a stack of photos on different focal planes, spaced by 1 um
        # Store initial position
        z0 = self.microscope.position()
        z = z0+arange(-5,6) # +- 5 um around current position
        stack = self.microscope.stack(self.camera, z, preprocessing = lambda img:crop_cardinal(crop_center(img),pipette_position))
        # Caution: image at depth -5 corresponds to the pipette being at depth +5 wrt the focal plane

        # Check microscope position
        if abs(z0-self.microscope.position())>position_tolerance:
            raise CalibrationError('Microscope has not returned to its initial position.')

        # Initial position of template in image
        sleep(sleep_time)
        image = self.camera.snap()
        x0, y0, _ = templatematching(image, stack[5])
        # Error margins for position estimation
        template_height, template_width = stack[5].shape
        xmargin = template_width/4
        ymargin = template_height/4

        # Calculate minimum correlation with stack images
        min_match = min([templatematching(image, template)[2] for template in stack])
        # We accept matches with matching correlation up to twice worse
        match_threshold = 1-(1-min_match)*2
        message('Matching threshold: '+str(match_threshold))

        # Store initial position of unit
        u0 = self.position()

        try:
            for axis in range(len(self.axes)):
                distance = 2.  # um
                ucurrent = 0  # current position of the axis relative to u0
                zcurrent = 0
                message('Calibrating axis '+str(axis))
                for k in range(7): # up to 128 um
                    message('Distance '+str(distance))
                    # 2) Move axis by a small displacement
                    self.relative_move(distance-ucurrent, axis)
                    ucurrent = distance
                    #self.absolute_move(u0[axis]+distance, axis)

                    # 3) Move focal plane by estimated amount (initially 0)
                    estimate = self.M[:,axis] * distance
                    xestimate, yestimate, zestimate = estimate
                    xestimate, yestimate = int(xestimate), int(yestimate)
                    #self.microscope.absolute_move(zestimate-z0)
                    self.microscope.relative_move(zestimate-zcurrent)
                    zcurrent = zestimate
                    self.microscope.wait_until_still()
                    self.wait_until_still(axis)

                    # Check microscope and axis positions
                    if abs(z0 + zcurrent - self.microscope.position()) > position_tolerance:
                        raise CalibrationError('Microscope has not moved to target position.')
                    if abs(u0[axis]+distance - self.position(axis)) > position_tolerance:
                        raise CalibrationError('Axis has not moved to target position.')

                    # 4) Estimate focal plane and position
                    sleep(sleep_time)
                    image = self.camera.snap()
                    # 4bis) Crop image around estimated position
                    image = image[y0+yestimate-ymargin:y0+yestimate+template_height+ymargin,
                                  x0+xestimate-xmargin:x0+xestimate+template_width+xmargin]

                    cv2.imwrite('./screenshots/focus{}.jpg'.format(k), image)
                    valmax = -1
                    for i,template in enumerate(stack): # we look for the best matching template
                        xt,yt,val = templatematching(image, template)
                        if val > valmax:
                            valmax=val
                            x,y,z = xt,yt,len(stack)/2-i # note the sign for z
                    if valmax<match_threshold:
                        raise CalibrationError('Matching error: the pipette is absent or not focused')

                    x+= x0+xestimate-xmargin
                    y+= y0+yestimate-ymargin

                    message('Camera x,y,z, correlation ='+str(x-x0)+','+str(y-y0)+','+str(z)+','+str(valmax))

                    # 5) Estimate matrix column; from unit to camera (first in pixels)
                    self.M[:,axis] = array([x-x0, y-y0, z+zestimate])/distance
                    message('Matrix column:'+str(self.M[:,axis]))

                    # 6) Multiply displacement by 2, and back to 2)
                    distance *=2

                # 7) Stop when predicted move is out of screen

                # Move back (not strictly necessary)
                self.relative_move(-ucurrent, axis)
                self.microscope.relative_move(-zcurrent)
                self.microscope.wait_until_still()
                self.wait_until_still(axis)
                # Check microscope and axis positions
                if abs(z0 - self.microscope.position()) > position_tolerance:
                    raise CalibrationError('Microscope has not returned to target position.')
                if abs(u0[axis] - self.position(axis)) > position_tolerance:
                    raise CalibrationError('Axis has not returned to initial position.')

            # Compute the (pseudo-)inverse
            self.Minv = pinv(self.M)

            # 8) Calculate conversion factor and offset.
            #    Offset is such that the initial position is (0,0,z0) in the reference system
            self.r0 = array([0,0,z0])-dot(self.M, u0)

            self.calibrated = True

        finally: # If something fails, move back to original position
            self.absolute_move(u0)
            self.microscope.absolute_move(z0)

    def calibrate_with_stage(self, message = lambda str: None):
        '''
        Automatic calibration of the manipulator using the camera.
        It is assumed that the pipette or some element attached to the unit is in the center of the image.
        The stage is moved so as to compensate for manipulator movement.

        Parameters
        ----------
        message : a function to which messages are passed
        '''
        # 0) Determine pipette cardinal position (N, S, E, W etc)
        pipette_position = pipette_cardinal(crop_center(self.camera.snap()))
        message("Pipette cardinal position: "+str(pipette_position))

        # 1) Take a stack of photos on different focal planes, spaced by 1 um
        # Store current position
        z0 = self.microscope.position()
        z = z0+arange(-5,6) # +- 5 um around current position
        stack = self.microscope.stack(self.camera, z, preprocessing = lambda img:crop_cardinal(crop_center(img),pipette_position))
        # Caution: image at depth -5 corresponds to the pipette being at depth +5 wrt the focal plane

        # Check microscope position
        if abs(z0-self.microscope.position())>position_tolerance:
            raise CalibrationError('Microscope has not returned to its initial position.')

        # Initial position of template in image
        sleep(sleep_time)
        image = self.camera.snap()
        x0, y0, _ = templatematching(image, stack[5])
        # Error margins for position estimation
        template_height, template_width = stack[5].shape
        xmargin = template_width/4
        ymargin = template_height/4

        # Calculate minimum correlation with stack images
        min_match = min([templatematching(image, template)[2] for template in stack])
        # We accept matches with a matching up to twice worse
        match_threshold = 1-(1-min_match)*2
        message('Matching threshold: '+str(match_threshold))

        # Store initial position of unit and stage
        u0 = self.position()
        stageu0 = self.stage.position()
        stager0 = self.stage.reference_position()

        try:
            for axis in range(len(self.axes)):
                distance = -2.*self.up_direction[axis]  # 2 um going down
                deltau = zeros(3)  # position of manipulator axes, relative to initial position
                previous_estimate = zeros(3)
                message('Calibrating axis '+str(axis))
                for k in range(7): # up to 128 um
                    message('Distance '+str(distance))
                    old_deltau = deltau.copy()
                    deltau[axis] = distance

                    # 2) Estimate target position on the camera
                    estimate = dot(self.M, deltau)
                    zestimate = estimate[2]
                    message('Estimated move:'+str(estimate))

                    # Check whether we might reach the floor (with 10% accuracy)
                    if self.microscope.floor_Z is not None:
                        if (zestimate-self.microscope.floor_Z)*self.microscope.up_direction<abs(distance)*.1:
                            message('We reached the coverslip, aborting.')
                            break
                    # Check whether unit position is reachable
                    if self.unit.min is not None:
                        if (u0+deltau<self.unit.min).any() | (u0+deltau>self.unit.max).any():
                            message('Pipette cannot reach next position, aborting.')
                            break

                    # 2bis) Move axis by a small displacement
                    self.relative_move(distance-old_deltau[axis], axis)

                    # 3) Move platform to center the pipette (compensating movement = opposite)
                    self.stage.reference_relative_move(previous_estimate-estimate)
                    self.stage.wait_until_still()
                    self.wait_until_still(axis)

                    # 3bis) Move focal plane by estimated amount (initially 0)
                    self.microscope.relative_move(zestimate-previous_estimate[2])
                    self.microscope.wait_until_still()

                    # Check microscope and axis positions
                    if abs(z0 + zestimate - self.microscope.position()) > position_tolerance:
                        raise CalibrationError('Microscope has not moved to target position.')
                    if abs(u0[axis]+distance - self.position(axis)) > position_tolerance:
                        raise CalibrationError('Axis has not moved to target position.')
                    if norm((stager0- estimate - self.stage.reference_position())[:2]) > position_tolerance:
                        raise CalibrationError('Stage has not moved to target position.')

                    previous_estimate = estimate

                    # 4) Estimate focal plane and position
                    sleep(sleep_time)
                    image = self.camera.snap()
                    # 4bis) Crop image around estimated position
                    image = image[y0-ymargin:y0+template_height+ymargin,
                                  x0-xmargin:x0+template_width+xmargin]

                    cv2.imwrite('./screenshots/focus{}.jpg'.format(k), image)
                    valmax = -1
                    for i,template in enumerate(stack): # we look for the best matching template
                        xt,yt,val = templatematching(image, template)
                        if val > valmax:
                            valmax=val
                            x,y,z = xt,yt,len(stack)/2-i # note the sign for z
                    if valmax<match_threshold:
                        raise CalibrationError('Matching error: the pipette is absent or not focused')
                    x+= x0-xmargin
                    y+= y0-ymargin

                    message('Camera x,y,z, correlation ='+str(x-x0)+','+str(y-y0)+','+str(z)+','+str(valmax))

                    # 5) Estimate matrix column; from unit to camera (first in pixels)
                    self.M[:,axis] = (array([x-x0, y-y0, z]) + estimate)/distance
                    message('Matrix column:'+str(self.M[:,axis]))

                    # 5bis) Determine pipette up direction
                    # We only need to it once, and we do it when the displacement is large enough
                    if (k == 4) & (axis == 0) & (self.microscope.up_direction is None):
                        positive_move = self.M[:,0]
                        self.up_direction[0] = up_direction(pipette_position, positive_move*sign(distance))
                        message('Axis 0 up direction: '+str(self.up_direction[0]))
                        # Now determine microscope up direction
                        self.microscope.up_direction = sign(self.M[2,0]*up_direction)
                        message('Microscope up direction: '+str(self.microscope.up_direction))
                    elif k==4:
                        # For other axes, we use microscope up direction
                        # If microscope up direction is provided, this is what we use too instead of guessing
                        self.up_direction[axis] = sign(self.M[2,axis]*self.microscope.up_direction)
                        message('Axis '+str(axis)+' up direction: ' + str(self.up_direction[0]))
                    # If we were actually going up, then we should now invert the direction
                    if distance * self.up_direction[axis] > 0:
                        message("Pipette was going up, now inverting direction")
                        distance = -distance

                    # 6) Multiply displacement by 2, and back to 2
                    distance *=2

                # Move back (not strictly necessary)
                # First move microscope up to avoid collisions
                self.microscope.relative_move(-estimate[2])
                self.microscope.wait_until_still()
                self.relative_move(-deltau[axis], axis)
                self.stage.reference_relative_move(estimate)
                self.wait_until_still(axis)
                self.stage.wait_until_still()
                # Check microscope, axis and stage positions
                if abs(z0 - self.microscope.position()) > position_tolerance:
                    raise CalibrationError('Microscope has not returned to target position.')
                if abs(u0[axis] - self.position(axis)) > position_tolerance:
                    raise CalibrationError('Axis has not returned to initial position.')
                if norm(stageu0 - self.stage.position()) > position_tolerance:
                    raise CalibrationError('Stage has not returned to initial position.')

            # Compute the (pseudo-)inverse
            self.Minv = pinv(self.M)

            # 8) Calculate conversion factor and offset.
            #    Offset is such that the initial position is (0,0,z0) in the reference system
            self.r0 = array([0,0,z0]) -dot(self.M, u0) - stager0

            self.calibrated = True

        finally: # If something fails, move back to original position
            # First move microscope up to avoid collisions
            self.microscope.absolute_move(z0)
            self.microscope.wait_until_still()
            self.absolute_move(u0)
            self.stage.absolute_move(stageu0)


class CalibratedStage(CalibratedUnit):
    '''
    A horizontal stage calibrated to a fixed reference coordinate system.
    The optional stage refers to a platform on which the unit is mounted, which can
    be None.
    The stage is assumed to be parallel to the focal plane (no autofocus needed)

    Parameters
    ----------
    unit : ManipulatorUnit for this stage
    stage : CalibratedUnit for a stage on which this stage might be mounted
    microscope : ManipulatorUnit for the microscope (single axis)
    camera : a camera, ie, object with a snap() method (optional, for visual calibration)
    '''
    def __init__(self, unit, stage=None, microscope=None, camera = None):
        CalibratedUnit.__init__(self, unit, stage, microscope, camera)
        # It should be an XY stage, ie, two axes
        if len(self.axes) != 2:
            raise CalibrationError('The unit should have exactly two axes for horizontal calibration.')

    def reference_move(self, r):
        if len(r)==2: # Third coordinate is actually not useful
            r3D = zeros(3)
            r3D[:2] = r
        else:
            r3D = r
        CalibratedUnit.reference_move(self,r3D) # Third coordinate is ignored

    def calibrate(self, message = lambda str: None):
        '''
        Automatic calibration for a horizontal XY stage

        Parameters
        ----------
        message : a function to which messages are passed
        '''
        if not self.stage.calibrated:
            self.stage.calibrate(message=message)

        # Take a photo of the pipette or coverslip
        template = crop_center(self.camera.snap())

        # Calculate the location of the template in the image
        sleep(sleep_time)
        image = self.camera.snap()
        x0, y0, _ = templatematching(image, template)

        # Store current position
        u0 = self.position()

        # 1) Move each axis by a small displacement (50 um)
        distance = 100. # in um
        for axis in range(len(self.axes)):  # normally just two axes
            self.relative_move(distance, axis) # there could be a keyword blocking = True
            self.wait_until_still(axis)
            sleep(sleep_time)
            image = self.camera.snap()
            x, y, _ = templatematching(image, template)
            message('Camera x,y =' + str(x - x0) + ',' + str(y - y0))

            # 2) Compute the matrix from unit to camera (first in pixels)
            self.M[:,axis] = array([x-x0, y-y0, 0])/distance
            message('Matrix column:' + str(self.M[:, axis]))
            x0, y0 = x, y # this is the position before the next move

        # Compute the (pseudo-)inverse
        self.Minv = pinv(self.M)
        # Offset is such that the initial position is zero in the reference system
        self.r0 = -dot(self.M, u0)
        self.calibrated = True

        # More accurate calibration:
        # 3) Move to three corners using the computed matrix
        width, height = self.camera.width, self.camera.height
        theight, twidth = template.shape # template dimensions
        # List of corners, reference coordinates
        # We use a margin of 1/4 of the template
        rtarget = [array([-(width/2-twidth*3./4),-(height/2-theight*3./4)]),
            array([(width/2-twidth*3./4),-(height/2-theight*3./4)]),
            array([-(width/2-twidth*3./4),(height/2-theight*3./4)])]
        u = []
        r = []
        for ri in rtarget:
            self.reference_move(ri)
            self.wait_until_still()
            sleep(sleep_time)
            image = self.camera.snap()
            x, y, _ = templatematching(image, template)
            message('Camera x,y =' + str(x - x0) + ',' + str(y - y0))
            r.append(array([x,y]))
            u.append(self.position())
        rx = r[1]-r[0]
        ry = r[2]-r[0]
        r = vstack((rx,ry)).T
        ux = u[1]-u[0]
        uy = u[2]-u[0]
        u = vstack((ux,uy)).T
        message('r: '+str(r))
        message('u: '+str(u))
        self.M[:2,:] = dot(r,inv(u))
        message('Matrix: ' + str(self.M))

        # 4) Recompute the matrix and the (pseudo) inverse
        self.Minv = pinv(self.M)

        # 5) Calculate conversion factor.

        # 6) Offset is such that the initial position is zero in the reference system
        self.r0 = -dot(self.M, u0)

        # Move back
        self.absolute_move(u0)
        self.wait_until_still()

    def mosaic(self, width = None, height = None):
        '''
        Takes a photo mosaic. Current position corresponds to
        the top left corner of the collated image.
        Stops when the unit's position is out of range, unless
        width and height are specified.

        Parameters
        ----------
        width : total width in pixel (optional)
        height : total height in pixel (optional)

        Returns
        -------
        A large image of the mosaic.
        '''
        u0=self.position()

        dx, dy = self.camera.width, self.camera.height
        # Number of moves in each direction
        nx = 1+int(width/dx)
        ny = 1+int(height/dy)
        # Big image
        big_image = zeros((ny*dy,nx*dx))

        column = 0
        xdirection = 1 # moving direction along x axis

        try:
            for row in range(ny):
                img = self.camera.snap()
                big_image[row*dy:(row+1)*dy, column*dx:(column+1)*dx] = img
                for _ in range(1,nx):
                    column+=xdirection
                    self.reference_relative_move([-dx*xdirection,0,0]) # sign: it's a compensatory move
                    self.wait_until_still()
                    sleep(0.1)
                    img = self.camera.snap()
                    big_image[row * dy:(row + 1) * dy, column * dx:(column + 1) * dx] = img
                if row<ny-1:
                    xdirection = -xdirection
                    self.reference_relative_move([0,-dy,0])
                    self.wait_until_still()
        finally: # move back to initial position
            self.absolute_move(u0)

        return big_image

class FixedStage(CalibratedUnit):
    '''
    A stage that cannot move. This is used to simplify the code.
    '''
    def __init__(self):
        self.r = array([0.,0.,0.]) # position in reference system
        self.u = array([0.,0.]) # position in stage system
        self.calibrated = True

    def position(self):
        return self.u

    def reference_position(self):
        return self.r

    def reference_move(self, r):
        # The fixed stage cannot move: maybe raise an error?
        pass

    def absolute_move(self, x, axis = None):
        pass