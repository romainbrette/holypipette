'''
A microscope class that is linked to a camera.
With methods to take a stack of images, autofocus, etc.

TODO:
* a umanager class that autoconfigures with umanager config file
* steps for stack acquisition?
* Perhaps this should not inherit ManipulatorUnit, but reimplement with single axis
'''
from devices.camera import *
from devices.manipulator import *
import time

class Microscope(ManipulatorUnit,Camera):
    '''
    A microscope Z axis with a camera.
    Not sure the camera should be tied to it (perhaps just passed to relevant methods).
    '''
    def __del__(self, manipulator, camera):
        ManipulatorUnit.__init__(manipulator.dev, manipulator.axes)
        if len(manipulator.axes)!=1:
            raise Exception('A microscope should have a single axis.')
        self.camera = camera

    # Redirection of camera methods (maybe not the best way to do it)
    def new_frame(self):
        return self.camera.new_frame()
    def snap(self):
        return self.camera.snap()
    def snap_center(self, ratio = 32):
        return self.camera.snap_center(ratio)

    def stack(self, z):
        '''
        Take a stack of images at the positions given in the z list

        Parameters
        ----------
        z : A list of z positions
        '''
        position = self.position()
        images = []
        for zi in range(z):
            self.absolute_move(zi)
            self.wait_until_still(zi)
            #time.sleep(1) # is this necessary?
            time.sleep(.1)
            images+= self.snap()
        self.absolute_move(position)
        return images
