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
