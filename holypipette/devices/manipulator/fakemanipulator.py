"""
A fake device useful for development.
It has 9 axes, numbered 1 to 9.
"""
from manipulator import Manipulator
from numpy import zeros

__all__ = ['FakeManipulator']

class FakeManipulator(Manipulator):
    def __init__(self):
        Manipulator.__init__(self)
        self.x = zeros(9) # Position of all axes

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
        self.x[axis-1] = x
        print 'Moved, new position: ', self.x
