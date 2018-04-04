from PyQt5 import QtCore, QtWidgets

from holypipette.interface import TaskInterface

class CameraInterface(TaskInterface):
    updated_exposure = QtCore.pyqtSignal('QString', 'QString')

    def __init__(self, camera):
        super(CameraInterface, self).__init__()
        self.camera = camera
        self.add_command('increase_exposure', 'Camera',
                         'Increase exposure time by {:.1f}ms',
                         default_arg=2.5)
        self.add_command('decrease_exposure', 'Camera',
                         'Decrease exposure time by {:.1f}ms',
                         default_arg=2.5)
        self.add_command('save_image', 'Camera',
                         'Save the current camera image to a file')

    def connect(self, main_gui):
        self.updated_exposure.connect(main_gui.set_status_message)
        self.signal_updated_exposure()

    def signal_updated_exposure(self):
        # Should be called by subclasses that actually support setting the exposure
        exposure = self.camera.get_exposure()
        if exposure > 0:
            self.updated_exposure.emit('Camera', 'Exposure: %.1fms' % exposure)

    def handle_command(self, command, argument):
        if command == 'increase_exposure':
            self.camera.change_exposure(2.5)
            self.signal_updated_exposure()
        elif command == 'decrease_exposure':
            self.camera.change_exposure(-2.5)
            self.signal_updated_exposure()
        elif command == 'save_image':
            self.save_image()
        else:
            raise ValueError('Unknown command: %s' % command)

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