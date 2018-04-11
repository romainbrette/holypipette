"""
A fake device useful for development.
It has 9 axes, numbered 1 to 9.
"""
from __future__ import print_function
from __future__ import absolute_import
from .manipulator import Manipulator
from numpy import zeros, clip

__all__ = ['FakeManipulator']

# TODO: Move in 3D
class FakeManipulator(Manipulator):
    def __init__(self, min=None, max=None):
        Manipulator.__init__(self)
        self.x = zeros(9) # Position of all axes
        # Minimum and maximum positions for all axes
        self.min = min
        self.max = max
        if (any([min is not None, max is not None]) and
                not all([min is not None, max is not None])):
            raise ValueError('Need to provide either both minimum and maximum '
                             'range or neither')
        if all([min is not None, max is not None]):
            if len(min) != 9 or len(max) != 9:
                raise ValueError('min/max argument needs to be a vector of '
                                 'length 9.')

    def position(self, axis):
        '''
        Current position along an axis.

        Parameters
        ----------
        axis : axis number

        Returns
        -------
        The current position of the device axis in um.
        '''
        return self.x[axis-1]

    def absolute_move(self, x, axis):
        '''
        Moves the device axis to position x.

        Parameters
        ----------
        axis: axis number
        x : target position in um.
        '''
        if self.min is None:
            self.x[axis-1] = x
        else:
            self.x[axis-1] = clip(x, self.min[axis-1], self.max[axis-1])
