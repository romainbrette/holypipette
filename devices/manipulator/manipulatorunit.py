"""
A class for access to a particular unit managed by a device

TODO:
* Some of these methods are specific to L&N (steps)
"""
from manipulator import Manipulator
from numpy import ndarray, sign
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


'''
The following 4 methods are specific to Luigs & Neumann manipulators.
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

    def step_move(self, distance, axis):
        '''
        Relative move using steps of up to 255 um.
        This fixes a bug on L&N controller.
        '''
        if isinstance(distance, ndarray):
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

    def set_ramp_length(self, axis, length):
        '''
        Sets the length of the ramp.
        Note: this is quite L&N specific.
        '''
        if isinstance(axis, list):
            for i in axis:
                self.set_ramp_length(i, length)
        else:
            self.dev.set_ramp_length(self.axes[axis], length)
        sleep(.05)

    def wait_until_still(self, axes):
        """
        Waits for the motors to stop.
        """
        if isinstance(axes, list):
            for i in axes:
                self.wait_until_still(i)
        else:
            self.dev.wait_motor_stop([self.axes[axes]])
        sleep(.05)
