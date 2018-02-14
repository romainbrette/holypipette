'''
A generic camera class

TODO:
* A stack() method which takes a series of photos along Z axis
'''
import numpy as np
import scipy.misc
from PyQt5 import QtCore

__all__ = ['Camera', 'FakeCamera']


class Camera(QtCore.QObject):
    updated_exposure = QtCore.pyqtSignal('QString', 'QString')

    def __init__(self):
        super(Camera, self).__init__()
        self.width = 1000
        self.height = 1000

    def connect(self, main_gui):
        self.updated_exposure.connect(main_gui.set_status_message)
        self.signal_updated_exposure()

    def signal_updated_exposure(self):
        # Should be called by subclasses that actually support setting the exposure
        exposure = self.get_exposure()
        if exposure > 0:
            self.updated_exposure.emit('Camera', 'Exposure: %.1fms' % exposure)

    @QtCore.pyqtSlot('QString')
    def handle_command(self, command):
        if command == 'increase_exposure':
            self.change_exposure(2.5)
        elif command == 'decrease_exposure':
            self.change_exposure(-2.5)
        else:
            raise ValueError('Uknown command: %s' % command)

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

    def set_exposure(self, value):
        print('Setting exposure time not supported for this camera')

    def get_exposure(self):
        print('Getting exposure time not supported for this camera')
        return -1

    def change_exposure(self, change):
        if self.get_exposure() > 0:
            self.set_exposure(self.get_exposure() + change)

    def reset(self):
        pass


class FakeCamera(Camera):

    # TODO: Connect this to FakeManipulator etc.
    def __init__(self):
        super(FakeCamera, self).__init__()
        self.width = 1024
        self.height = 768
        self.frame = scipy.misc.face(gray=True)
        self.exposure_time = 30

    def set_exposure(self, value):
        if 0 < value <= 200:
            self.exposure_time = value
            self.signal_updated_exposure()

    def get_exposure(self):
        return self.exposure_time

    def snap(self):
        '''
        Returns the current image.
        This is a blocking call (wait until next frame is available)
        '''
        exposure_factor = self.exposure_time/30.
        noisy_frame = self.frame + np.random.randn(self.height, self.width)*10
        return np.array(np.clip(noisy_frame*exposure_factor, 0, 255),
                        dtype=np.uint8)
