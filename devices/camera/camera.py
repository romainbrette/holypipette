'''
A generic camera class

TODO:
* A stack() method which takes a series of photos along Z axis
'''

__all__ = ['Camera']


class Camera(object):
    def __init__(self):
        self.width = 1000
        self.height = 1000

    def new_frame(self):
        '''
        Returns True if a new frame is available
        '''
        return True

    def snap(self):
        '''
        Returns the current image
        '''
        return None

    def snap_center(self, ratio = 32):
        '''
        Returns the center of the image.

        Parameters
        ----------
        ratio : size ratio of cropped image to original image
        '''
        image = self.snap()
        shape = [self.height, self.width]
        cropped = image.frame[shape[0] / 2 - 3 * shape[0] / ratio:shape[0] / 2 + 3 * shape[0] / ratio,
                             shape[1] / 2 - 3 * shape[1] / ratio:shape[1] / 2 + 3 * shape[1] / ratio]
        return cropped

