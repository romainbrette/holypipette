"""
Prior Proscan III Stage control.
"""
from __future__ import print_function
import warnings
from .manipulator import Manipulator
#from manipulator import Manipulator
import sys
import time
import numpy as np
sys.path.append('C:\\Program Files\\Micro-Manager-1.4')
try:
    import MMCorePy
except ImportError: # Micromanager not installed
    warnings.warn('Micromanager is not installed, cannot use the Prior class.')

__all__ = ['Prior']


class Prior(Manipulator):
    def __init__(self):
        Manipulator.__init__(self)
        mmc = MMCorePy.CMMCore()
        self.mmc = mmc
        self.mmc.loadSystemConfiguration("C:\Program Files\Micro-Manager-1.4\MMConfig_demo.cfg")

    def position(self, axis):
        if axis == 0:
            return self.mmc.getXPosition('XYStage')
        if axis == 1:
            return self.mmc.getYPosition('XYStage')
        if axis == 2:
            return self.mmc.getPosition('ZStage')

    def position_group(self, axes):
        axes4 = [0, 0, 0, 0]
        for i in range(len(axes)):
            axes4[i] = self.position(axis = axes[i])
        return np.array(axes4[:len(axes)])

    def absolute_move(self, x, axis):
        if axis == 0:
            self.mmc.setXYPosition('XYStage', x, self.mmc.getYPosition('XYStage'))
        if axis == 1:
            self.mmc.setXYPosition('XYStage', self.mmc.getXPosition('XYStage'), x)
        if axis == 2:
            self.mmc.setPosition('ZStage', x)

    def absolute_move_group(self, x, axes):
        for i in range(len(axes)):
            self.absolute_move(x[i], axes[i])
            self.wait_until_still()

    def relative_move(self, x, axis):
        if axis == 0:
            self.mmc.setRelativeXYPosition('XYStage', x, 0)
        if axis == 1:
            self.mmc.setRelativeXYPosition('XYStage', 0, x)
        if axis == 2:
            self.mmc.setRelativePosition('ZStage', x)

    def wait_until_still(self, axes = None, axis = None):
        self.mmc.waitForSystem()
        self.sleep(.7) # That's a very long time!

    def stop(self):
        self.mmc.stop()


if __name__ == '__main__':
    prior = Prior()
    print(prior.position(axis = 1))
    #prior.relative_move(50,axis =1)
    #prior.wait_until_still()
    print(prior.position(axis=1))


