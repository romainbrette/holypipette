# coding=utf-8
"""
A class to handle a manipulator unit with coordinates calibrated to the reference system of a camera.
It contains methods to calibrate the unit.

Should messages be issued?
Also ranges should be taken into account

Should this be in devices/ ? Maybe in a separate calibration folder
"""
from __future__ import print_function
from __future__ import absolute_import
from .manipulatorunit import *
from numpy import (array, zeros, dot, arange, vstack, sign, pi, arcsin,
                   mean, std, isnan)
from numpy.linalg import inv, pinv, norm
from holypipette.vision import *


__all__ = ['CalibratedUnit', 'CalibrationError', 'CalibratedStage']

verbose = True

##### Calibration parameters #####
from holypipette.config import Config, NumberWithUnit, Number


class CalibrationConfig(Config):
    position_tolerance = NumberWithUnit(0.5, unit='μm',
                                        doc='Position tolerance',
                                        bounds=(0, 10))
    sleep_time = NumberWithUnit(1., unit='s',
                                doc='Sleep time before taking pictures',
                                bounds=(0, 2))
    stack_depth = NumberWithUnit(8, unit='μm', doc='Depth of stack of photos',
                                 bounds=(0, 20))
    calibration_moves = Number(9, doc='Number of calibration moves',
                               bounds=(1, 20))
    position_update = NumberWithUnit(1000, unit='ms',
                                     doc='Update displayed position every',
                                     bounds=(0, 10000))
    categories = [('Calibration', ['sleep_time', 'position_tolerance',
                                   'stack_depth', 'calibration_moves']),
                  ('Display', ['position_update'])]


class CalibrationError(Exception):
    def __init__(self, message='Device is not calibrated'):
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
    def __init__(self, unit, stage=None, microscope=None, camera=None,
                 config=None):
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
        self.saved_state_question = ('Move manipulator and stage back to '
                                     'initial position?')
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
        self.up_direction = [-1 for _ in range(len(unit.axes))] # Default up direction, determined during calibration

        self.pipette_position = None
        self.photos = None
        self.photo_x0 = None
        self.photo_y0 = None

        # Matrices for passing to the camera/microscope system
        self.M = zeros((3,len(unit.axes))) # unit to camera
        self.Minv = zeros((len(unit.axes),3)) # Inverse of M, when well defined (otherwise pseudoinverse? pinv)
        self.r0 = zeros(3) # Offset in reference system

        # Dictionary of objectives and conditions (immersed/non immersed)
        #self.objective = dict()

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
        Position in the reference camera system.

        Returns
        -------
        The current position in um as an XYZ vector.
        '''
        if not self.calibrated:
            raise CalibrationError
        u = self.position() # position vector in manipulator unit system
        return dot(self.M, u) + self.r0 + self.stage.reference_position()

    def reference_move(self, r, safe = False):
        '''
        Moves the unit to position r in reference camera system, without moving the stage.

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
            if (z-z0)*self.up_direction[2]>0: # going up
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

    def withdraw(self):
        '''
        Withdraw the pipette to the upper end position
        '''
        if self.up_direction[0]>0:
            position = self.max[0]
        else:
            position = self.min[0]
        self.absolute_move(position, axis=0)

    def focus(self):
        '''
        Move the microscope so as to put the pipette tip in focus
        '''
        self.microscope.absolute_move(self.reference_position()[2])
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
        if (r[2] - uprime[2])*self.microscope.up_direction<0:
            # Movement is down
            # First, we determine the intersection between the line going through x
            # with direction corresponding to the manipulator first axis.
            alpha = (uprime - r)[2] / self.M[2,0]
            # TODO: check whether the intermediate move is accessible

            # Intermediate move
            self.reference_move(r + alpha * p, safe = True)
            # We need to wait here!
            self.wait_until_still()

        # Recalibrate 100 um before target; only if distance is greater than 500 um
        if recalibrate & (length>500):
            self.reference_move(r + 50 * p * self.up_direction[0],safe=True)
            self.wait_until_still()
            z0 = self.microscope.position()
            self.focus()
            self.auto_recalibrate(center=False)
            self.microscope.absolute_move(z0)
            self.microscope.wait_until_still()

        # Final move
        self.reference_move(r + withdraw * p * self.up_direction[0], safe = True) # Or relative move in manipulator coordinates, first axis (faster)

    def take_photos(self, rig = 1):
        '''
        Take photos of the pipette. It is assumed that the pipette is centered and in focus.
        '''
        self.info('Taking photos of pipette')
        if rig == 1:
            self.pipette_position = pipette_cardinal(crop_center(self.camera.snap()))
        else:
            distance = 100
            self.relative_move(distance, 0)
            self.wait_until_still(0)
            self.sleep(0.1)
            img1 = crop_center(self.camera.snap())
            self.relative_move(-distance, 0)
            self.wait_until_still(0)
            self.sleep(0.1)
            img2 = crop_center(self.camera.snap())
            self.pipette_position = pipette_cardinal2(img1, img2)

        self.info("Pipette cardinal position: "+str(self.pipette_position))

        z0 = self.microscope.position()
        z = z0 + arange(-self.config.stack_depth, self.config.stack_depth + 1)  # +- stack_depth um around current position
        stack = self.microscope.stack(self.camera, z, preprocessing=lambda img: crop_cardinal(crop_center(img), self.pipette_position),
                                      save = 'series')
        # Caution: image at depth -5 corresponds to the pipette being at depth +5 wrt the focal plane

        # Check microscope position
        if abs(z0-self.microscope.position())>self.config.position_tolerance:
            raise CalibrationError('Microscope has not returned to its initial position.')
        self.sleep(self.config.sleep_time)
        image = self.camera.snap()
        x0, y0, _ = templatematching(image, stack[self.config.stack_depth])

        # Calculate minimum correlation with stack images
        image = stack[len(stack)//2] # Focused image
        min_match = min([templatematching(image, template)[2] for template in stack])
        # We accept matches with matching correlation up to twice worse
        self.min_photo_match = min_match

        self.photos = stack
        self.photo_x0 = x0
        self.photo_y0 = y0

    def pixel_per_um(self):
        '''
        Returns the objective magnification in pixel per um, calculated for each manipulator axis.
        '''
        p = []
        for axis in range(len(self.axes)):
            p.append(((self.M[0,axis]**2 + self.M[1,axis]**2)/(1-self.M[2,axis]**2))**.5)
        return p

    def analyze_calibration(self):
        '''
        Analyzes calibration matrices.
        '''
        # Objective magnification
        print("Magnification for each axis of the pipette: "+str(self.pixel_per_um()[:2]))
        pixel_per_um = self.stage.pixel_per_um()[0]
        print("Magnification for each axis of the stage: "+str(pixel_per_um))
        print("Field size: "+str(self.camera.width/pixel_per_um)+" µm x "+str(self.camera.height/pixel_per_um)+' µm')
        # Pipette vs. stage (for each axis, mvt should correspond to 1 um)
        for axis in range(len(self.axes)):
            compensating_move = -dot(self.stage.Minv,self.M[:,axis])
            length = (sum(compensating_move[:2]**2)+self.M[2,axis]**2)**.5
            print("Precision of axis "+str(axis)+": "+str(abs(1-length)))
            # Angles
            angle = abs(180/pi * arcsin(self.M[2,axis] / length))
            print('Angle of axis '+str(axis)+": "+str(angle))

    def move_new_pipette_back(self):
        '''
        Moves a new (uncalibrated) pipette back under the microscope
        '''
        # First move it 2 mm before target position
        withdraw = 2000.
        self.reference_move(array([0,0,self.microscope.position()])+ withdraw * self.M[:,0] * self.up_direction[0])
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
            self.absolute_move(self.position(0)-100. * self.up_direction[0], 0)
            self.wait_until_still(0)
            I = std(self.camera.snap())
            if abs(I-I0)>sigma:
                found = True
                break

        if found:
            self.info('Pipette found! with change = '+str(abs(I-I0)/I0))
        else:
            self.info('Pipette not found')

    # ***** REFACTORING OF CALIBRATION ****
    def locate_pipette(self, threshold=None, depth=None, return_correlation=False):
        '''
        Locates the pipette on screen, using photos previously taken.

        Parameters
        ----------
        threshold : correlation threshold
        depth : maximum distance in z to search; if None, only uses the depth of the photo stack
        return_correlation : if True, returns the best correlation in the template matching

        Returns
        -------
        x,y,z : position on screen relative to center
        '''
        stack = self.photos

        if depth is not None:
            # Move the focus so as explore a larger depth
            z0 = self.microscope.position()
            z = -depth+len(stack)/2
            valmax = -1
            while z<depth+len(stack)/2:
                self.debug('Depth: '+str(z))
                self.microscope.absolute_move(z0 + z)
                self.microscope.wait_until_still()
                x,y,zt,c = self.locate_pipette(threshold=threshold, depth=None, return_correlation=True)
                if c>valmax:
                    xm,ym,zm,valmax = x,y,z+zt,c
                z += len(stack)
            self.microscope.absolute_move(z0)
            self.microscope.wait_until_still()
            self.info('Pipette identified at depth '+str(zm))
            if return_correlation:
                return xm,ym,zm,valmax
            else:
                return xm,ym,zm

        x0, y0 = self.photo_x0, self.photo_y0
        if threshold is None:
            threshold = 1-(1-self.min_photo_match)*2

        image = self.camera.snap()

        # Error margins for position estimation
        template_height, template_width = stack[self.config.stack_depth].shape
        xmargin = template_width / 4
        ymargin = template_height / 4

        # First template matching to estimate pipette position on screen
        xt, yt, _ = templatematching(image, stack[self.config.stack_depth])

        image = self.camera.snap()
        # Crop image around estimated position
        image = image[int(yt - ymargin):int(yt + template_height + ymargin),
                      int(xt - xmargin):int(xt + template_width + xmargin)]
        dx = xt - xmargin
        dy = yt - ymargin

        valmax = -1
        for i, template in enumerate(stack):  # we look for the best matching template
            xt, yt, val = templatematching(image, template)
            xt += dx
            yt += dy
            if val > valmax:
                valmax = val
                x, y, z = xt, yt, self.config.stack_depth - i  # note the sign for z

        self.debug('Correlation=' + str(valmax))
        if valmax < threshold:
            raise CalibrationError('Matching error: the pipette is absent or not focused')

        self.info('Pipette identified at x,y,z=' + str(x - x0) + ',' + str(y - y0) + ',' + str(z))

        if return_correlation:
            return x-x0, y-y0, z, valmax
        else:
            return x-x0, y-y0, z

    def move_and_track(self, distance, axis, M, move_stage=False):
        '''
        Moves along one axis and track the pipette with microscope and optionally the stage.

        Arguments
        ---------
        distance : distance to move
        axis : axis number

        Returns
        -------
        x,y,z: pipette position on screen and focal plane
        '''
        self.relative_move(distance, axis)
        self.abort_if_requested()
        # Estimate movement on screen
        estimate = M[:, axis]*distance

        # Move the stage to compensate
        if move_stage:
            self.abort_if_requested()
            self.stage.reference_relative_move(-estimate)
            self.stage.wait_until_still()

        self.abort_if_requested()

        # Autofocus
        self.wait_until_still(axis) # Wait until pipette has moved
        self.microscope.relative_move(estimate[2])
        self.microscope.wait_until_still()

        # Locate pipette
        self.sleep(self.config.sleep_time)
        x, y, z = self.locate_pipette()
        self.abort_if_requested()
        # Focus, move stage and locate again
        self.microscope.relative_move(z)
        if move_stage:
            self.abort_if_requested()
            self.stage.reference_relative_move(-array([x, y, 0]))
            self.stage.wait_until_still()
        self.abort_if_requested()
        self.microscope.wait_until_still()
        self.sleep(self.config.sleep_time)
        self.abort_if_requested()
        x, y, z = self.locate_pipette()

        return x, y, z

    def move_back(self, z0, u0, us0=None):
        '''
        Moves back up to original position, refocus and locate pipette

        Arguments
        ---------
        z0 : microscope position
        u0 : unit position
        us0 : stage position

        Returns
        -------
        x,y,z : pipette position on screen and focal plane
        '''
        # Move back
        self.microscope.absolute_move(z0)
        self.microscope.wait_until_still()
        self.abort_if_requested()
        self.absolute_move(u0)
        if us0 is not None: # stage moves too
            self.abort_if_requested()
            self.stage.absolute_move(us0)
            self.stage.wait_until_still()
        self.abort_if_requested()
        self.wait_until_still()

        # Locate pipette
        self.sleep(self.config.sleep_time)
        _, _, z = self.locate_pipette()

        self.abort_if_requested()

        # Focus and locate again
        self.microscope.relative_move(z)
        self.microscope.wait_until_still()
        self.sleep(self.config.sleep_time)
        x, y, z = self.locate_pipette()

        return x,y,z

    def calculate_up_directions(self, M):
        '''
        Calculates up directions for all axes and microscope from the matrix.
        '''
        # Determine up direction for the first axis (assumed to be the main axis)
        positive_move = 1*M[:, 0] # move of 1 um along first axis
        self.debug('Positive move: {}'.format(positive_move))
        self.up_direction[0] = up_direction(self.pipette_position, positive_move)
        self.info('Axis 0 up direction: ' + str(self.up_direction[0]))

        # Determine microscope up direction
        if self.microscope.up_direction is None:
            self.microscope.up_direction = sign(M[2, 0])
        self.info('Microscope up direction: ' + str(self.microscope.up_direction))

        # Determine up direction of other axes
        for axis in range(1,len(self.axes)):
            # We use microscope up direction
            s = sign(M[2, axis] * self.microscope.up_direction)
            if s != 0:
                self.up_direction[axis] = s
            self.info('Axis ' + str(axis) + ' up direction: ' + str(self.up_direction[0]))

    def calibrate(self, rig =1):
        '''
        Automatic calibration.
        Starts without moving the stage, then moves the stage (unless it is fixed).
        '''
        # *** Calibrate the stage ***
        self.info('Calibrating stage first')
        self.stage.calibrate()
        self.abort_if_requested()
        # *** Take photos ***
        # Take a stack of photos on different focal planes, spaced by 1 um
        if rig ==1:
            self.take_photos()
        else:
            self.take_photos(rig = 2)

        # *** Calculate image borders ***

        template_height, template_width = self.photos[self.config.stack_depth].shape
        width, height = self.camera.width, self.camera.height
        # We use a margin of 1/4 of the template
        left_border = -(width/2-(template_width*3)/4)
        right_border = (width/2-(template_width*3)/4)
        top_border = -(height/2-(template_height*3)/4)
        bottom_border = (height/2-(template_height*3)/4)

        # *** Store initial position ***
        z0 = self.microscope.position()
        u0 = self.position()
        us0 = self.stage.position()

        self.info('First matrix estimation (move each axis once)')
        # *** First pass: move each axis once and estimate matrix ***
        M = zeros((3, len(self.axes)))
        distance = self.config.stack_depth*.5
        self.debug('Distance: {}'.format(distance))
        oldx, oldy, oldz = 0., 0., self.microscope.position() # Initial position on screen: centered and focused
        for axis in range(len(self.axes)):
            self.debug('Moving axis {}'.format(axis))
            x, y, z = self.move_and_track(distance, axis, M, move_stage=False)
            z += self.microscope.position()
            self.debug('x={}, y={}, z={}'.format(x, y, z))
            M[:, axis] = array([x-oldx, y-oldy, z-oldz]) / distance
            oldx, oldy, oldz = x, y, z
        self.debug('Matrix:' + str(M))

        # *** Calculate up directions ***
        self.calculate_up_directions(M)

        self.info('Moving back to initial position')
        # Move back to initial position
        oldx, oldy, oldz = self.move_back(z0, u0, None)  # The pipette could have moved
        oldz += self.microscope.position()

        # Calculate floor (min Z)
        if self.microscope.up_direction>0:
            self.microscope.floor_Z = self.microscope.min
        else:
            self.microscope.floor_Z = self.microscope.max

        if self.microscope.floor_Z is None: # If min Z not provided, assume 300 um margin
            floor = z0-300.*self.microscope.up_direction
            self.debug('Setting floor to {} (300 um below current position)'.format(floor))
        else:
            floor = self.microscope.floor_Z

        self.info('Estimating the matrix with increasingly large movements')
        # *** Estimate the matrix using increasingly large movements ***
        min_distance = distance
        for axis in range(len(self.axes)):
            self.debug('Calibrating axis ' + str(axis))
            distance = min_distance * 1.
            oldrs = self.stage.reference_position()
            move_stage = False
            moves = 0
            while moves < self.config.calibration_moves: # just for testing
                moves += 1
                distance *= 2
                self.debug('Distance ' + str(distance))

                # Check whether the next position might be unreachable
                future_position = self.position(axis) - distance*self.up_direction[axis]
                if (future_position<self.min[axis]) | (future_position>self.max[axis]):
                    self.info("Next move cannot be performed (end position)")
                    break

                # Estimate final position on screen
                dxe, dye, dze = -self.M[:, axis] * distance * self.up_direction[axis]
                xe, ye, ze = oldx+dxe, oldy+dye, oldz+dze

                # Check whether we might be out of field
                if (xe<left_border) | (xe>right_border) | (ye<top_border) | (ye>bottom_border):
                    self.info('Next move is out of field')
                    if not self.fixed:
                        move_stage = True # Move the stage to recenter
                    else:
                        break

                # Check whether we might reach the floor (with 100 um margin)
                if (ze - floor) * self.microscope.up_direction < 100.:
                    self.info('We reached the coverslip (z={z}, floor={floor}, microscope up={up}).'.format(z=ze, floor=floor, up=self.microscope.up_direction))
                    break

                self.abort_if_requested()
                # Move pipette down
                x, y, z = self.move_and_track(-distance*self.up_direction[axis], axis, M,
                                              move_stage=move_stage)
                rs = self.stage.reference_position()

                # Update matrix
                z += self.microscope.position()
                M[:, axis] = -(array([x - oldx, y - oldy, z - oldz])+oldrs-rs) / distance*self.up_direction[axis]
                oldx, oldy, oldz = x, y, z
                oldrs = rs

            # Move back to initial position
            u = self.position(axis)
            self.debug('Moving back over '+str(u0[axis]-u)+' um')
            oldrs = self.stage.reference_position() # Normally not necessary
            x, y, z = self.move_back(z0, u0, us0)
            rs = self.stage.reference_position()
            # Update matrix
            z += self.microscope.position()
            M[:, axis] = (array([x - oldx, y - oldy, z - oldz]) + oldrs-rs) / (u0[axis]-u)
            oldx, oldy, oldz = x, y, z

        self.debug('Final Matrix:' + str(M))

        if not isnan(M).any():
            # *** Compute the (pseudo-)inverse ***
            Minv = pinv(M)

            # *** Calculate offset ***0
            #    Offset is such that the initial position is the position on screen in the reference system
            r0 = array([x, y, z]) - dot(M, u0) - self.stage.reference_position()

            # Store the new values
            self.M = M
            self.Minv = Minv
            self.r0 = r0
            self.calibrated = True
        else:
            raise CalibrationError('Matrix contains NaN values')

    # TODO: Is this function still used?
    def calibrate2(self):
        '''
        Automatic calibration.
        Second algorithm: moves along axes of the reference system.
        '''
        # *** Calibrate the stage ***
        self.stage.calibrate()

        # *** Take photos ***
        # Take a stack of photos on different focal planes, spaced by 1 um
        self.take_photos()

        # *** Calculate image borders ***

        template_height, template_width = self.photos[self.config.stack_depth].shape
        width, height = self.camera.width, self.camera.height
        # We use a margin of 1/4 of the template
        left_border = -(width/2-(template_width*3)/4)
        right_border = (width/2-(template_width*3)/4)
        top_border = -(height/2-(template_height*3)/4)
        bottom_border = (height/2-(template_height*3)/4)

        # *** Store initial position ***
        z0 = self.microscope.position()
        u0 = self.position()
        us0 = self.stage.position()

        # *** First pass: move each axis once and estimate matrix ***
        self.Minv = 0*self.Minv # Erase current matrix
        distance = self.config.stack_depth*.5
        oldx, oldy, oldz = 0., 0., self.microscope.position() # Initial position on screen: centered and focused
        for axis in range(len(self.axes)):
            x,y,z = self.move_and_track(distance, axis, move_stage=False)
            z+= self.microscope.position()
            self.debug('x={}, y={}, z={}'.format(x, y, z))
            self.M[:, axis] = array([x-oldx, y-oldy, z-oldz]) / distance
            oldx, oldy, oldz = x, y, z
        self.debug('Matrix:' + str(self.M))

        # *** Calculate up directions ***
        self.calculate_up_directions()

        # Move back to initial position
        oldx, oldy, oldz = self.move_back(z0, u0, None)  # The pipette could have moved
        oldz+=self.microscope.position()

        # Calculate floor (min Z)
        if self.microscope.floor_Z is None: # If min Z not provided, assume 300 um margin
            floor = z0-300.*self.microscope.up_direction
        else:
            floor = self.microscope.floor_Z

        # *** Estimate the matrix using increasingly large movements ***
        min_distance = distance
        for axis in range(3):
            self.info('Calibrating axis ' + str(axis))
            distance = min_distance * 1.
            oldrs = self.stage.reference_position()
            move_stage = False
            while (distance<300): # just for testing
                distance *= 2
                self.debug('Distance ' + str(distance))

                # Move pipette
                move = zeros(3)
                if (axis == 2):
                    # move pipette down
                    move[axis] = -distance*self.microscope.up_direction[axis]
                else:
                    move[axis] = distance # we should move in a direction that does not collide with the objective

                next_u = self.position()+dot(self.Minv, move)
                next_us = self.stage.position()-dot(self.stage.Minv, move)

                # Check whether we might reach the floor (with 100 um margin)
                if (next_u[2] - floor) * self.microscope.up_direction < 100.:
                    self.info('We reached the coverslip.')
                    break

                # Check whether we might exceed the limits
                if (next_u < self.min).any() | (next_u > self.max).any() | \
                   (next_us < self.stage.min).any() | (next_us > self.stage.max).any():
                    self.info('Next position is not reachable')
                    break

                self.reference_relative_move(move)
                self.wait_until_still()
                if (axis==2):
                    self.microscope.relative_move(move[2])
                    self.microscope.wait_until_still()
                self.stage.reference_relative_move(-move)
                self.stage.wait_until_still()

                x,y,z = self.locate_pipette()

                # Update matrix
                z += self.microscope.position()
                r = array([x,y,z])-array([oldx,oldy,oldz])
                self.Minv[:, axis] = dot(self.Minv,move+r) / move[axis]

                # Adjust
                self.stage.reference_relative_move(-array([x,y,0]))
                self.microscope.relative_move(z)
                x,y,z = self.locate_pipette()

                oldx, oldy, oldz = x, y, z

            # Move back to initial position
            x, y, z = self.move_back(z0, u0, us0)
            z += self.microscope.position()
            oldx, oldy, oldz = x, y, z

        self.debug('Matrix:' + str(self.M))

        # *** Compute the (pseudo-)inverse ***
        self.M = pinv(self.Minv)

        # *** Calculate offset ***0
        #    Offset is such that the initial position is the position on screen in the reference system
        self.r0 = array([x, y, z]) - dot(self.M, u0) - self.stage.reference_position()

        self.calibrated = True

    def recalibrate(self, xy=(0,0)):
        '''
        Recalibrates the unit by shifting the reference frame (r0).
        It assumes that the pipette is centered on screen.
        '''
        #    Offset is such that the position is (x,y,z0) in the reference system
        u0 = self.position()
        z0 = self.microscope.position()
        stager0 = self.stage.reference_position()
        x,y = xy
        r0 = array([x, y, z0]) - dot(self.M, u0) - stager0
        self.r0 = r0

    def manual_calibration(self, landmarks):
        '''
        Calibrates the unit based on 4 landmarks.
        The stage must be properly calibrated.
        '''
        landmark_r, landmark_u, landmark_rs = landmarks
        self.debug('landmark r: ' + str(landmark_r))

        # r is the reference position (screen + focal plane)
        r0 = landmark_r[0]
        r = array([(r-r0) for r in landmark_r[1:]]).T
        rs0 = landmark_rs[0]
        rs = array([(rs-rs0) for rs in landmark_rs[1:]]).T
        u0 = landmark_u[0]
        u = array([(u-u0) for u in landmark_u[1:]]).T

        self.debug('r: '+str(r))
        self.debug('rs: ' + str(rs))
        self.debug('u: '+str(u))
        M = dot(r-rs,inv(u))
        self.debug('Matrix: ' + str(M))

        # 4) Recompute the matrix and the (pseudo) inverse
        Minv = pinv(M)

        # 5) Calculate conversion factor.

        # Offset (doesn't seem to be right)
        r0 = r0-rs0-dot(M, u0)
        self.M = M
        self.Minv = Minv
        self.r0 = r0
        self.calibrated = True

    def auto_recalibrate(self, center=True):
        '''
        Recalibrates the unit by shifting the reference frame (r0).
        The pipette is visually identified using a stack of photos.

        Parameters
        ----------
        center : if True, move stage and focus to center the pipette
        '''
        self.info('Automatic recalibration')
        x,y,z = self.locate_pipette(depth=50) # 50 um
        z+= self.microscope.position()
        self.info('Pipette at z='+str(z))

        u0 = self.position()
        stager0 = self.stage.reference_position()

        # Offset is such that the position is (x,y,z) in the reference system
        self.r0 = array([x,y,z]) - dot(self.M, u0) - stager0

        # Move to center pipette
        if center:
            self.debug('Center pipette')
            self.microscope.absolute_move(z)
            self.abort_if_requested()
            self.stage.reference_relative_move(-array([x,y]))
        self.wait_until_still()

    def save_configuration(self):
        '''
        Outputs configuration in a dictionary.
        '''
        config = {'up_direction' : self.up_direction,
                  'M' : self.M,
                  'r0' : self.r0,
                  'pipette_position' : self.pipette_position,
                  'photos' : self.photos,
                  'photo_x0' : self.photo_x0,
                  'photo_y0' : self.photo_y0,
                  'min' : self.min,
                  'max' : self.max}

        return config

    def load_configuration(self, config):
        '''
        Loads configuration from dictionary config.
        Variables not present in the dictionary are untouched.
        '''
        self.up_direction = config.get('up_direction', self.up_direction)
        self.M = config.get('M', self.M)
        if 'M' in config:
            self.Minv = pinv(self.M)
            self.calibrated = True
        self.r0 = config.get('r0', self.r0)
        self.pipette_position = config.get('pipette_position', self.pipette_position)
        self.photos = config.get('photos', self.photos)
        self.photo_x0 = config.get('photo_x0', self.photo_x0)
        self.photo_y0 = config.get('photo_y0', self.photo_y0)
        self.min = config.get('min', self.min)
        self.max = config.get('max', self.max)


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
    camera : a camera, ie, object with a ``snap()`` method (optional, for visual calibration)
    '''
    def __init__(self, unit, stage=None, microscope=None, camera=None,
                 config=None):
        CalibratedUnit.__init__(self, unit, stage, microscope, camera,
                                config=config)
        self.saved_state_question = 'Move stage back to initial position?'
        # It should be an XY stage, ie, two axes
        if len(self.axes) != 2:
            raise CalibrationError('The unit should have exactly two axes for horizontal calibration.')

    def reference_move(self, r):
        if len(r)==2: # Third coordinate is actually not useful
            r3D = zeros(3)
            r3D[:2] = r
        else:
            r3D = r
        CalibratedUnit.reference_move(self, r3D) # Third coordinate is ignored

    def calibrate(self):
        '''
        Automatic calibration for a horizontal XY stage

        '''
        if not self.stage.calibrated:
            self.stage.calibrate()

        self.info('Preparing stage calibration')
        # Take a photo of the pipette or coverslip
        template = crop_center(self.camera.snap())

        # Calculate the location of the template in the image
        self.sleep(self.config.sleep_time)
        image = self.camera.snap()
        x0, y0, _ = templatematching(image, template)

        M = zeros((3, len(self.axes)))

        # Store current position
        u0 = self.position()
        self.info('Small movements for each axis')
        # 1) Move each axis by a small displacement (50 um)
        distance = 40. # in um
        for axis in range(len(self.axes)):  # normally just two axes
            self.abort_if_requested()
            self.relative_move(distance, axis) # there could be a keyword blocking = True
            self.wait_until_still(axis)
            self.sleep(self.config.sleep_time)
            self.abort_if_requested()
            image = self.camera.snap()
            x, y, _ = templatematching(image, template)
            self.debug('Camera x,y =' + str(x - x0) + ',' + str(y - y0))

            # 2) Compute the matrix from unit to camera (first in pixels)
            M[:,axis] = array([x-x0, y-y0, 0])/distance
            self.debug('Matrix column:' + str(M[:, axis]))
            x0, y0 = x, y # this is the position before the next move

        # Compute the (pseudo-)inverse
        Minv = pinv(M)
        # Offset is such that the initial position is zero in the reference system
        r0 = -dot(M, u0)

        # Store the results
        self.M = M
        self.Minv = Minv
        self.r0 = r0
        self.calibrated = True

        self.info('Large displacements')

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
            self.abort_if_requested()
            self.reference_move(ri)
            self.wait_until_still()
            self.sleep(self.config.sleep_time)
            image = self.camera.snap()
            x, y, _ = templatematching(image, template)
            self.debug('Camera x,y =' + str(x - x0) + ',' + str(y - y0))
            r.append(array([x,y]))
            u.append(self.position())
        rx = r[1]-r[0]
        ry = r[2]-r[0]
        r = vstack((rx,ry)).T
        ux = u[1]-u[0]
        uy = u[2]-u[0]
        u = vstack((ux,uy)).T
        self.debug('r: '+str(r))
        self.debug('u: '+str(u))
        M[:2, :] = dot(r, inv(u))
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

        self.info('Moving back')
        # Move back
        self.absolute_move(u0)
        self.wait_until_still()
        self.info('Stage calibration done')

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