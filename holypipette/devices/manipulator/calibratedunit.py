# coding=utf-8
"""
A class to handle a manipulator unit with coordinates calibrated to a fixed reference system
(typically the stage).
It contains methods to calibrate the unit.

Manipulator directions (+-1) must be set so that x>0 means going down (advancing the axis) and z>0 means going up.

TODO:
- move_new_pipette_back: use a large relative_move and abort
- CalibratedStage.calibrate : calibrate camera
"""
from __future__ import print_function
from __future__ import absolute_import
from .manipulatorunit import *
from numpy import (array, zeros, dot, arange, vstack, sign, pi, arcsin,
                   mean, std, isnan, cos, sin)
from numpy.linalg import inv, pinv, norm
from holypipette.vision import *


__all__ = ['CalibratedUnit', 'CalibrationError', 'CalibratedStage', 'CalibratedCamera', 'CalibratedMicroscope',
           'CalibrationConfig']

verbose = True

##### Calibration parameters #####
from holypipette.config import Config, NumberWithUnit, Number, Boolean


class CalibrationConfig(Config):
    position_update = NumberWithUnit(1000, unit='ms',
                                     doc='Update displayed position every',
                                     bounds=(0, 10000))
    categories = [('Display', ['position_update'])]


class CalibrationError(Exception):
    def __init__(self, message='Device is not calibrated'):
        self.message = message

    def __str__(self):
        return self.message


class CalibratedCamera(object):
    def __init__(self, camera=None):
        '''
        A camera calibrated to a fixed reference coordinate system.

        Parameters
        ----------
        camera : a camera, ie, object with a snap() method (optional, for visual calibration)
        '''
        self.calibrated = False
        self.camera = camera

        # Matrices for passing from reference system to camera system
        self.M = zeros((2,2)) # unit to camera
        self.Minv = zeros((2,2)) # Inverse of M, when well defined (otherwise pseudoinverse? pinv)
        self.r0 = zeros(2) # Offset in reference system

    def camera_position(self, p):
        '''
        Position in the camera system.

        Parameters
        ----------
        p : XY position in um in the reference system.

        Returns
        -------
        The camera position in pixel as an XY vector.
        '''
        if not self.calibrated:
            raise CalibrationError
        return dot(self.M, p) + self.r0

    def reference_position(self, y):
        '''
        Position in the reference system.

        Parameters
        ----------
        y : XY position in pixel in the camera system.

        Returns
        -------
        The position in um as an XY vector.
        '''
        if not self.calibrated:
            raise CalibrationError
        return dot(self.Minv, y - self.r0)

    def reference_movement(self, y):
        '''
        Movement vector in the reference system.

        Parameters
        ----------
        y : XY vector in pixel in the camera system.

        Returns
        -------
        The movement in um as an XY vector.
        '''
        if not self.calibrated:
            raise CalibrationError
        return dot(self.Minv, y)

    def pixel_per_um(self, M=None):
        '''
        Returns the objective magnification in pixel per um, calculated for each reference axis.
        '''
        if M is None:
            M = self.M
        p = []
        for axis in range(2):
            p.append(((M[0,axis]**2 + M[1,axis]**2))**.5)
        return p

    def analyze_calibration(self):
        '''
        Analyzes calibration matrices.
        '''
        # Objective magnification
        pixel_per_um = self.pixel_per_um()
        print("Magnification for each axis: "+str(pixel_per_um))
        print("Field size: "+str(self.camera.width/pixel_per_um[0])+" µm x "+str(self.camera.height/pixel_per_um[1])+' µm')

    def save_configuration(self):
        '''
        Outputs configuration in a dictionary.
        '''
        config = {'M' : self.M,
                  'r0' : self.r0}

        return config

    def load_configuration(self, config):
        '''
        Loads configuration from dictionary config.
        Variables not present in the dictionary are untouched.
        '''
        self.M = config.get('M', self.M)
        if 'M' in config:
            self.Minv = pinv(self.M)
            self.calibrated = True
        self.r0 = config.get('r0', self.r0)

    def snap(self):
        '''
        Returns the current image
        '''
        return self.camera.snap()


class CalibratedUnit(ManipulatorUnit):
    def __init__(self, unit, stage=None, microscope=None, camera=None,
                 config=None, direction=None, alpha=0., theta=0.):
        '''
        A manipulator unit calibrated to a fixed reference coordinate system.
        The stage refers to a platform on which the unit is mounted, which can
        be None.

        For a manipulator, this gives the position of the tip.
        For a stage, it gives the position of the stage center.

        Parameters
        ----------
        unit : ManipulatorUnit for the (XYZ) unit
        stage : CalibratedUnit for the stage
        microscope : ManipulatorUnit for the microscope (single axis)
        camera : CalibratedCamera (optional)
        direction : vector of +-1 directions
        alpha : horizontal angle of the manipulator, in degree
        theta : vertical angle of the manipulator, in degree
        '''
        ManipulatorUnit.__init__(self, unit.dev, unit.axes)
        if config is None:
            config = CalibrationConfig(name='Calibration config')
        self.config = config
        if stage is None: # In this case we assume the unit is on a fixed element.
            self.stage = FixedStage()
            self.fixed = True
        else:
            self.stage = stage
            self.fixed = False
        self.microscope = microscope
        self.camera = camera

        self.calibrated = False
        self.direction = direction # Direction for each axis (+- 1)
        self.alpha = alpha
        self.theta = theta

        # Matrices for passing to the camera/microscope system
        self.M = zeros((3,len(unit.axes))) # unit to camera
        self.Minv = zeros((len(unit.axes),3)) # Inverse of M, when well defined (otherwise pseudoinverse? pinv)
        self.r0 = zeros(3) # Offset in reference system

        self.build_matrix()

    def build_matrix(self):
        '''
        Builds the transformation matrix from angles.
        '''
        if self.M.sum() == 0.: # not calculated yet
            direction = zeros(3)
            direction[:len(self.direction)] = self.direction
            self.M = array([[direction[0]*cos(self.alpha*pi/180)*cos(self.theta*pi/180), -direction[1]*sin(self.alpha*pi/180), 0.],
                            [direction[0]*sin(self.alpha*pi/180)*cos(self.theta*pi/180), direction[1]*cos(self.alpha*pi/180), 0.],
                            [direction[0]*sin(self.theta*pi/180), 0., direction[2]]])[:len(self.direction), :len(self.direction)]
            self.Minv = pinv(self.M)
            self.calibrated = True

    def save_state(self):
        if self.stage is not None:
            self.stage.save_state()
        if self.microscope is not None:
            self.microscope.save_state()
        self.saved_state = self.position()

    def delete_state(self):
        if self.stage is not None:
            self.stage.delete_state()
        if self.microscope is not None:
            self.microscope.delete_state()
        self.saved_state = None

    def recover_state(self):
        if self.stage is not None:
            self.stage.recover_state()
        if self.microscope is not None:
            self.microscope.recover_state()
        self.absolute_move(self.saved_state)

    def reference_position(self):
        '''
        Position in the reference system.

        Returns
        -------
        The current position in um as an XYZ vector.
        '''
        if not self.calibrated:
            raise CalibrationError
        u = self.position() # position vector in manipulator unit system
        return dot(self.M, u) + self.r0 + self.stage.reference_position()

    def camera_position(self):
        '''
        Position in the camera system.

        Returns
        -------
        The current position in um as an XYZ vector.
        '''
        return self.camera.camera_position(self.reference_position())

    def reference_move_not_X(self, r):
        '''
        Moves the unit to position r in reference system, without moving the stage,
        but without moving the X axis (so this can be done last).

        Parameters
        ----------
        r : XYZ position vector in um
        safe : if True, moves the Z axis first or last, so as to avoid touching the coverslip
        '''
        if not self.calibrated:
            raise CalibrationError
        u = dot(self.Minv, r-self.stage.reference_position()-self.r0)
        u[0] = self.position(axis=0)
        self.absolute_move(u)

    def reference_move_not_Z(self, r):
        '''
        Moves the unit to position r in reference system, without moving the stage,
        but without moving the Z axis (so this can be done last).

        Parameters
        ----------
        r : XYZ position vector in um
        safe : if True, moves the Z axis first or last, so as to avoid touching the coverslip
        '''
        if not self.calibrated:
            raise CalibrationError
        u = dot(self.Minv, r-self.stage.reference_position()-self.r0)
        u[0] = self.position(axis=2)
        self.absolute_move(u)

    def reference_move(self, r, safe = False):
        '''
        Moves the unit to position r in reference system, without moving the stage.

        Parameters
        ----------
        r : XYZ position vector in um
        safe : if True, moves the Z axis first or last, so as to avoid touching the coverslip
        '''
        if not self.calibrated:
            raise CalibrationError
        u = dot(self.Minv, r-self.stage.reference_position()-self.r0)
        if safe:
            z0 = self.position(axis=2)
            z = u[2]
            if z-z0>0: # going up
                # Go up first
                self.absolute_move(z,axis=2)
                self.wait_until_still(2)
                self.absolute_move(u)
            else: # going down
                # Go down first
                uprime = u.copy()
                u[2] = z0
                self.absolute_move(uprime)
                self.wait_until_still()
                self.absolute_move(z,axis=2)
        else:
            self.absolute_move(u)

    def camera_move(self, p, safe = False):
        '''
        Moves the unit to position p in camera system, without moving the stage.
        The third coordinate is the z position in the reference system.

        Parameters
        ----------
        p : XYZ position vector, XY in pixel, Z in um
        safe : if True, moves the Z axis first or last, so as to avoid touching the coverslip
        '''
        r = zeros(3)
        r[:2] = self.camera.reference_position(p[:2])
        r[2] = p[2]
        self.reference_move(r, safe=safe)

    def reference_relative_move(self, r):
        '''
        Moves the unit by vector r in reference system, without moving the stage.

        Parameters
        ----------
        r : XYZ position vector in um
        '''
        if not self.calibrated:
            raise CalibrationError
        u = dot(self.Minv, r)
        self.relative_move(u)

    def camera_relative_move(self, p):
        '''
        Moves the unit by vector p in camera system, without moving the stage.
        The third coordinate is the z position in the reference system.

        Parameters
        ----------
        p : XYZ position vector, XY in pixel, Z in um
        '''
        r = zeros(3)
        r[:2] = self.camera.reference_movement(p[:2])
        r[2] = p[2]
        self.reference_relative_move(r)

    def focus(self):
        '''
        Move the microscope so as to put the pipette tip in focus
        '''
        self.microscope.reference_move(self.reference_position()[2])
        self.microscope.wait_until_still()

    def safe_move(self, r, withdraw = 0., recalibrate = False):
        '''
        Moves the device to position x (an XYZ vector) in a way that minimizes
        interaction with tissue.

        If the movement is down, the manipulator is first moved horizontally,
        then along the pipette axis.
        If the movement is up, a direct move is done.

        Parameters
        ----------
        r : target position in um, an (X,Y,Z) vector
        withdraw : in um; if not 0, the pipette is withdrawn by this value from the target position x
        recalibrate : if True, pipette is recalibrated 1 mm before its target
        '''
        if not self.calibrated:
            raise CalibrationError

        # Calculate length of the move
        length = norm(dot(self.Minv,r-self.reference_position()))

        p = self.M[:,0] # this is the vector for the first manipulator axis
        uprime = self.reference_position() # I should call this uprime but rprime

        # First we check whether movement is up or down
        if (r[2] - uprime[2])<0:
            # Movement is down
            # First, we determine the intersection between the line going through x
            # with direction corresponding to the manipulator first axis.
            alpha = (uprime - r)[2] / self.M[2,0]
            # TODO: check whether the intermediate move is accessible

            # Intermediate move
            self.reference_move(r + alpha * p, safe = True)
            # We need to wait here!
            self.wait_until_still()

        # Final move
        self.reference_move(r - withdraw * p, safe = True) # Or relative move in manipulator coordinates, first axis (faster)


    def move_new_pipette_back(self):
        '''
        Moves a new (uncalibrated) pipette back under the microscope
        '''
        # First move it 2 mm before target position
        withdraw = 2000.
        self.reference_move(array([0,0,self.microscope.reference_position()])- withdraw * self.M[:,0])
        self.wait_until_still()

        # Take photos to analyze the mean contrast (not exactly)
        images=[]
        for _ in range(10):
            images.append(std(self.camera.snap()))
            self.sleep(0.1)
        I0 = mean(images)
        sigma = I0*.2 # allow for a 20% change
        self.debug('Contrast: '+str(I0)+" +- "+str(sigma))

        # Move by steps of 100 um until the contrast changes
        found = False
        for i in range(50): # 5 mm maximum
            self.debug('Moving down, i='+str(i))
            #self.relative_move(-50.*self.up_direction[0],0)
            # absolute move just to ensure it's fast
            self.absolute_move(self.position(0)+100., 0)
            self.wait_until_still(0)
            I = std(self.camera.snap())
            if abs(I-I0)>sigma:
                found = True
                break

        if found:
            self.info('Pipette found! with change = '+str(abs(I-I0)/I0))
        else:
            self.info('Pipette not found')


    def measure_theta(self, p):
        '''
        Measure vertical angle by comparing the current position with another position in focus.
        '''
        new_p = self.position()
        self.theta = 180/pi*arcsin(abs((new_p[2] - p[2])/(new_p[0] - p[0])))
        self.debug('theta ='+str(self.theta))
        # Rebuild the matrix
        self.M[:] = 0.
        self.build_matrix()

    def recalibrate(self, xy=(0,0)):
        '''
        Recalibrates the unit by shifting the reference frame (r0).
        It assumes that the pipette is centered on screen.

        TODO: map xy in pixel to um
        '''
        #    Offset is such that the position is (x,y,z0) in the reference system
        u0 = self.position()
        z0 = self.microscope.reference_position()
        stager0 = self.stage.reference_position()
        x,y = xy
        r0 = array([x, y, z0]) - dot(self.M, u0) - stager0
        self.r0 = r0


    def save_configuration(self):
        '''
        Outputs configuration in a dictionary.
        '''
        config = {'direction' : self.direction,
                  'M' : self.M,
                  'theta' : self.theta,
                  'r0' : self.r0}

        return config


    def load_configuration(self, config):
        '''
        Loads configuration from dictionary config.
        Variables not present in the dictionary are untouched.
        '''
        self.direction = config.get('direction', self.direction)
        self.M = config.get('M', self.M)
        if 'M' in config:
            self.Minv = pinv(self.M)
            self.calibrated = True
        self.r0 = config.get('r0', self.r0)
        self.theta = config.get('theta', self.theta)
        self.build_matrix()


class CalibratedMicroscope(CalibratedUnit):
    def __init__(self, microscope, config=None, direction=None):
        '''
        A motorized microscope calibrated to a fixed reference coordinate system.
        It just needs a direction, such that z<0 means going down.
        '''
        CalibratedUnit.__init__(self, microscope, stage=None,
                                config=config, direction=[direction])
        self.calibrated = True


class CalibratedStage(CalibratedUnit):
    '''
    A horizontal stage calibrated to a fixed reference coordinate system.
    The optional stage refers to a platform on which the unit is mounted, which can
    be None.
    The stage is assumed to be parallel to the focal plane.

    Parameters
    ----------
    unit : ManipulatorUnit for this stage
    stage : CalibratedUnit for a stage on which this stage might be mounted
    microscope : ManipulatorUnit for the microscope (single axis)
    camera : CalibratedCamera (optional)
    direction : vector of +-1 directions for axes
    '''
    def __init__(self, unit, stage=None, microscope=None, camera=None,
                 config=None, direction=None):
        CalibratedUnit.__init__(self, unit, stage, microscope, camera,
                                config=config, direction=direction)
        # It should be an XY stage, ie, two axes
        if len(self.axes) != 2:
            raise CalibrationError('The unit should have exactly two axes for horizontal calibration.')

    def recalibrate(self, xy=(0,0)):
        '''
        Sets the current position as the central position, i.e., X=Y=0.
        '''
        CalibratedUnit.recalibrate(xy=xy)
        self.r0[2] = 0.


    def reference_move(self, r):
        if len(r)==2: # Third coordinate is actually not useful
            r3D = zeros(3)
            r3D[:2] = r
        else:
            r3D = r
        CalibratedUnit.reference_move(self, r3D) # Third coordinate is ignored

    def reference_relative_move(self, r):
        if len(r)==2: # Third coordinate is actually not useful
            r3D = zeros(3)
            r3D[:2] = r
        else:
            r3D = r
        CalibratedUnit.reference_relative_move(self, r3D) # Third coordinate is ignored

    def equalize_matrix(self, M=None):
        '''
        Equalizes the length of columns in a matrix, by default the current transformation matrix
        '''
        if M is None:
            return_M = False
            M = self.M
        else:
            return_M = True
        # We compute the quadratic mean
        pixel_per_um = ((M**2).sum(axis=0))**.5 # Assuming it is a 2D matrix (the third component is 0)
        self.debug('{} pixels per um'.format(pixel_per_um))
        mean_pixel_per_um = ((pixel_per_um**2).mean())**.5 # quadratic mean
        for axis in range(len(self.axes)):
            M[:, axis] = M[:, axis] * mean_pixel_per_um / pixel_per_um[axis]
        if return_M:
            return M
        else:
            self.M = M


    def calibrate(self):
        '''
        Automatic calibration for a horizontal XY stage
        '''
        if not self.stage.calibrated:
            self.stage.calibrate()

        self.info('Preparing stage calibration')
        # Take a photo of the pipette or coverslip
        template = crop_center(self.camera.snap(), ratio=64)

        # Calculate the location of the template in the image
        self.sleep(self.config.sleep_time)
        image = self.camera.snap()
        x0, y0, _ = templatematching(image, template)
        previousx, previousy = x0, y0

        M = zeros((3, len(self.axes)))

        # Store current position
        u0 = self.position()
        self.info('Small movements for each axis')
        # 1) Move each axis by a small displacement (40 um)
        distance = 40. # in um
        for axis in range(len(self.axes)):  # normally just two axes
            self.abort_if_requested()
            self.relative_move(distance, axis) # there could be a keyword blocking = True
            self.wait_until_still(axis)
            self.sleep(self.config.sleep_time)
            self.abort_if_requested()
            image = self.camera.snap()
            x, y, _ = templatematching(image, template)
            self.debug('Camera x,y =' + str(x - previousx) + ',' + str(y - previousy))

            # 2) Compute the matrix from unit to camera (first in pixels)
            M[:,axis] = array([x-previousx, y-previousy, 0])/distance
            self.debug('Matrix column:' + str(M[:, axis]))
            previousx, previousy = x, y # this is the position before the next move

        # Equalize axes (same displacement in each direction); for the movement it's not done
        if self.config.equalize_axes:
            M = self.equalize_matrix(M)

        # Compute the (pseudo-)inverse
        self.M = M
        Minv = pinv(M)
        # Offset is such that the initial position is zero in the reference system
        r0 = -dot(M, u0)

        # Store the results
        self.Minv = Minv
        self.r0 = r0
        self.calibrated = True

        self.info('Large displacements')
        # More accurate calibration:
        # 3) Move to three corners using the computed matrix
        scale = 0.9  # This is to avoid the black corners
        width, height = int(self.camera.width * scale), int(self.camera.height * scale)
        theight, twidth = template.shape  # template dimensions
        # List of corners, reference coordinates
        # We use a margin of 1/4 of the template
        rtarget = [array([-(width / 2 - twidth * 3. / 4), -(height / 2 - theight * 3. / 4)]),
                   array([(width / 2 - twidth * 3. / 4), -(height / 2 - theight * 3. / 4)]),
                   array([-(width / 2 - twidth * 3. / 4), (height / 2 - theight * 3. / 4)])]


        best_error = 1e6
        best_M, best_Minv = M, Minv
        for _ in range(int(self.config.stage_refine_steps)+1):
            self.info('Moving back')

            # Move back
            self.absolute_move(u0)
            self.wait_until_still()
            self.sleep(self.config.sleep_time)

            # Fix any residual error (due to motor unreliability)
            image = self.camera.snap()
            x, y, _ = templatematching(image, template)
            self.debug('Camera x,y =' + str(x - x0) + ',' + str(y - y0))

            # Recenter
            self.reference_relative_move(-array([x - x0, y - y0]))
            self.wait_until_still()
            u0 = self.position()
            self.r0 = -dot(M, u0)

            u = []
            r = []
            for ri in rtarget:
                self.abort_if_requested()
                self.reference_move(ri)
                self.wait_until_still()
                self.sleep(self.config.sleep_time)
                image = self.camera.snap()
                # Template matching could be reduced to the expected region
                x, y, _ = templatematching(image, template)
                # Error calculation
                self.debug('Camera x,y = {},{}'.format(x - x0,y - y0))
                r.append(array([x-x0,y-y0]))
                u.append(self.position())
            # Error
            quadratic_error = array([(rtarget[i] - r[i])**2 for i in range(3)]).mean()
            self.debug('Error = {} pixels'.format(quadratic_error**.5))

            # Is it better than previously?
            if quadratic_error<best_error:
                best_error = quadratic_error
                best_M, best_Minv = M, Minv

            rx = r[1]-r[0]
            ry = r[2]-r[0]
            r = vstack((rx,ry)).T
            ux = u[1]-u[0]
            uy = u[2]-u[0]
            u = vstack((ux,uy)).T
            self.debug('r: '+str(r))
            self.debug('u: '+str(u))
            M[:2, :] = dot(r, inv(u))
            if self.config.equalize_axes:
                M = self.equalize_matrix(M)
            self.debug('Matrix: ' + str(M))

            # 4) Recompute the matrix and the (pseudo) inverse
            Minv = pinv(M)

            # 5) Calculate conversion factor.

            # 6) Offset is such that the initial position is zero in the reference system
            r0 = -dot(M, u0)

            # Store results
            self.M = M
            self.Minv = Minv
            self.r0 = r0

        # Select the best one
        if (int(self.config.stage_refine_steps)>0):
            self.M = best_M
            self.Minf = best_Minv

        # Move back and recenter
        self.info('Moving back')
        self.absolute_move(u0)
        self.wait_until_still()
        self.sleep(self.config.sleep_time)

        image = self.camera.snap()
        x, y, _ = templatematching(image, template)
        self.debug('Camera x,y =' + str(x - x0) + ',' + str(y - y0))

        self.reference_relative_move(-array([x-x0, y-y0]))
        self.r0 = -dot(M, u0)

        self.info('Stage calibration done')
        if (int(self.config.stage_refine_steps)>0): # otherwise it's not measurable
            self.info('Error = {} pixels = {} %'.format(best_error**.5,
                                                        100*(best_error**.5)/max([width,height])))

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
                    self.sleep(0.1)
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
        self.stage = None
        self.microscope = None
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