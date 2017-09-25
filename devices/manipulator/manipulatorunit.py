"""
A class for access to a particular unit managed by a device.
It is essentially a subset of a Manipulator

TODO:
* Some of these methods are specific to L&N (steps)
"""
from manipulator import Manipulator
from numpy import ndarray, sign, ones, arange
from time import sleep

__all__ = ['ManipulatorUnit']


class ManipulatorUnit(Manipulator):
    def __init__(self, dev, axes):
        '''
        Parameters
        ----------
        dev : underlying device
        axes : list of 3 axis indexes
        '''
        Manipulator.__init__(self)
        self.dev = dev
        self.axes = axes
        # Motor ranges in um
        self.min = None
        self.max = None

    def position(self, axis = None):
        '''
        Current position along an axis.

        Parameters
        ----------
        axis : axis number starting at 0; if None, all XYZ axes

        Returns
        -------
        The current position of the device axis in um.
        '''
        if axis is None: # all positions in a vector
            #return array([self.dev.position(self.axes[axis]) for axis in range(len(self.axes))])
            return self.dev.position_group(self.axes)
        else:
            return self.dev.position(self.axes[axis])

    def absolute_move(self, x, axis = None):
        '''
        Moves the device axis to position x in um.

        Parameters
        ----------
        axis : axis number starting at 0; if None, all XYZ axes
        x : target position in um.
        '''
        if axis is None:
            # then we move all axes
            #for i, axis in enumerate(self.axes):
            #    self.dev.absolute_move(x[i], axis)
            self.dev.absolute_move_group(x, self.axes)
        else:
            self.dev.absolute_move(x, self.axes[axis])
        sleep(.05)

    def absolute_move_group(self, x, axes):
        ## What is this??
        '''
        if isinstance(x, ndarray):
            pos = []
            for j in range(len(x)):
                for i in range(len(x[j])):
                    pos += [x[j, i]]
        else:
            pos = x

        if len(pos) != len(axes):
            raise ValueError('Length of arrays do not match.')
        '''
        self.dev.absolute_move_group(x, [self.axes[i] for i in axes])
        sleep(.05)

    def relative_move(self, x, axis = None):
        '''
        Moves the device axis by relative amount x in um.

        Parameters
        ----------
        axis : axis number starting at 0; if None, all XYZ axes
        x : position shift in um.
        '''
        if axis is None:
            # then we move all axes
            #for i, axis in enumerate(self.axes):
            #    self.dev.relative_move(x[i], axis)
            self.dev.relative_move_group(x, self.axes)
        else:
            self.dev.relative_move(x, self.axes[axis])
        sleep(.05)

    def stop(self, axis = None):
        """
        Stop current movements.
        """
        if axis is None:
            # then we stop all axes
            for i, axis in enumerate(self.axes):
                self.dev.stop(axis)
        else:
            self.dev.stop(self.axes[axis])

    def motor_ranges(self):
        """
        Runs the motors to calculate ranges of the motors.
        """
        dx = ones(len(self.axes)) * 1000000. # (1 meter; should more than any platform)
        self.relative_move(-dx)
        self.wait_until_still()
        self.min = self.position()
        self.relative_move(dx)
        self.wait_until_still()
        self.max = self.position()

    def is_accessible(self, x, axis = None):
        """
        Checks whether position x is accessible.
        """
        if axis is None:
            return all([self.is_accessible(x[i]) for i in range(self.axes)])
        else:
            return (x>=min) and (x<=max)

    '''
    The following 3 methods are specific to Luigs & Neumann manipulators.
    This is used in calibration.
    Maybe have a keyword failsafe = True in relative_move?
    '''
    def single_step(self, axis, step):
        '''
        Moves by a single step.
        '''
        if isinstance(axis, list):
            for i in axis:
                self.single_step(i, step)
        else:
            self.dev.single_step(self.axes[axis], step)
        sleep(.05)

    def set_single_step_distance(self, axis, distance):
        '''
        Sets single step distance.
        '''
        if isinstance(axis, list):
            for i in axis:
                self.set_single_step_distance(i, distance)
        else:
            self.dev.set_single_step_distance(self.axes[axis], distance)
        sleep(.05)

    def step_move(self, distance, axis=None):
        '''
        Relative move using steps of up to 255 um.
        This fixes a bug on L&N controller.
        '''
        if axis is None:
            for i in range(len(self.axes)):
                self.step_move(distance[i],i)
        elif isinstance(distance, ndarray):
            move = []
            for j in range(len(distance)):
                for i in range(len(distance[j])):
                    move += [distance[j, i]]
            self.step_move(move, axis)
        elif isinstance(distance, list):
            if len(distance) != len(axis):
                raise ValueError('Length of arguments do not match')
            for i in range(len(distance)):
                self.step_move(distance[i], axis[i])
        else:
            number_step = abs(distance) // 255
            last_step = abs(distance) % 255
            if number_step:
                self.set_single_step_distance(axis, 255)
                self.single_step(axis, number_step*sign(distance))
            if last_step:
                self.set_single_step_distance(axis, last_step)
                self.single_step(axis, sign(distance))

    def wait_until_still(self, axes = None):
        """
        Waits for the motors to stop.
        """
        if axes is None: # all axes
            axes = range(len(self.axes))
        if isinstance(axes, list): # is that useful?
            for i in axes:
                self.wait_until_still(i)
        else:
            self.dev.wait_until_still([self.axes[axes]])
        sleep(.05)
