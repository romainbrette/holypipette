'''
A microscope is a manipulator with a single axis.
With methods to take a stack of images, autofocus, etc.

TODO:
* a umanager class that autoconfigures with umanager config file
* steps for stack acquisition?
'''
from devices.manipulator import *
import time
import cv2

__all__ = ['Microscope']

class Microscope(Manipulator):
    '''
    A microscope Z axis, obtained here from an axis of a Manipulator.
    '''
    def __init__(self, dev, axis):
        '''
        Parameters
        ----------
        dev : underlying device
        axis : axis index
        '''
        Manipulator.__init__(self)
        self.dev = dev
        self.axis = axis

    def position(self):
        '''
        Current position

        Returns
        -------
        The current position of the device axis in um.
        '''
        return self.dev.position(self.axis)

    def absolute_move(self, x):
        '''
        Moves the device axis to position x in um.

        Parameters
        ----------
        x : target position in um.
        '''
        self.dev.absolute_move(x, self.axis)

    def relative_move(self, x):
        '''
        Moves the device axis by relative amount x in um.

        Parameters
        ----------
        x : position shift in um.
        '''
        self.dev.relative_move(x, self.axis)

    def stop(self):
        """
        Stop current movements.
        """
        self.dev.stop(self.axis)

    def wait_until_still(self):
        """
        Waits for the motors to stop.
        """
        self.dev.wait_until_still([self.axis])

    def stack(self, camera, z, preprocessing=lambda img:img, save = True):
        '''
        Take a stack of images at the positions given in the z list

        Parameters
        ----------
        camera : a camera, eg with a snap() method
        z : A list of z positions
        preprocessing : a function that processes the images (optional)
        save : saves images to disk if True
        '''
        position = self.position()
        images = []
        k = 0
        for zi in z:
            self.absolute_move(zi)
            self.wait_until_still()
            #time.sleep(1) # is this necessary?
            time.sleep(.1)
            img = preprocessing(camera.snap())
            images.append(img)
            cv2.imwrite('./screenshots/series{}.jpg'.format(k), img)
            k+=1
        self.absolute_move(position)
        return images
