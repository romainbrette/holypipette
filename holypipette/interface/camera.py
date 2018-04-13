from __future__ import print_function
from PyQt5 import QtCore, QtWidgets

from holypipette.interface import TaskInterface, command


class CameraInterface(TaskInterface):
    updated_exposure = QtCore.pyqtSignal('QString', 'QString')

    def __init__(self, camera):
        super(CameraInterface, self).__init__()
        self.camera = camera

    def connect(self, main_gui):
        self.updated_exposure.connect(main_gui.set_status_message)
        self.signal_updated_exposure()

    def signal_updated_exposure(self):
        # Should be called by subclasses that actually support setting the exposure
        exposure = self.camera.get_exposure()
        if exposure > 0:
            self.updated_exposure.emit('Camera', 'Exposure: %.1fms' % exposure)

    @command(category='Camera',
             description='Increase exposure time by {:.1f}ms',
             default_arg=2.5)
    def increase_exposure(self, increase):
        self.camera.change_exposure(2.5)
        self.signal_updated_exposure()

    @command(category='Camera',
             description='Increase exposure time by {:.1f}ms',
             default_arg=2.5)
    def decrease_exposure(self, increase):
        self.camera.change_exposure(-2.5)
        self.signal_updated_exposure()

    @command(category='Camera',
             description='Save the current image to a file')
    def save_image(self):
        try:
            import imageio
        except ImportError:
            print('Saving images needs imageio')
            return
        frame = self.camera.snap()
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(caption='Save image',
                                                         filter='Images (*.png, *.tiff)')
        if len(fname):
            imageio.imwrite(fname, frame)
