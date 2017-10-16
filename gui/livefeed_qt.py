from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from devices.camera.umanagercamera import Lumenera

__all__ = ['LiveFeedQt']

def insert_cross(image):
    width, height = image.shape[:2]
    if len(image.shape) == 3:  # color image
        image[width//2-10:width//2+10, height//2, :] = (0, 0, 200)
        image[width//2, height//2-10:height//2+10, :] = (0, 0, 200)
    else:  # grayscale image
        image[width//2-10:width//2+10, height//2] = 0
        image[width//2, height//2-10:height//2+10] = 0
    return image


class ClickableLabel(QtWidgets.QLabel):
    def __init__(self, callback=None):
        self.callback = callback
        super(ClickableLabel, self).__init__()

    def mousePressEvent(self, event):
        if self.callback is not None:
            self.callback(event)


class LiveFeedQt(QtWidgets.QScrollArea):
    def __init__(self, camera, mouse_callback=None,
                 image_edit=insert_cross):
        super(LiveFeedQt, self).__init__()
        self.image_edit = image_edit

        self.camera = camera
        self.width, self.height = self.camera.width, self.camera.height
        self.imageLabel = ClickableLabel(mouse_callback)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setWidget(self.imageLabel)

        self.update_image()
        self.imageLabel.adjustSize()

        self.resize(self.imageLabel.sizeHint())

        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_image)
        timer.start(33) #30 Hz

    @QtCore.pyqtSlot()
    def update_image(self):
        # get data and display
        frame = self.camera.snap()
        if len(frame.shape) == 2:
            # Grayscale image via MicroManager
            bytesPerLine = self.width
            format = QtGui.QImage.Format_Grayscale8
        else:
            # Color image via OpenCV
            bytesPerLine = 3*self.width
            format = QtGui.QImage.Format_RGB888

        frame = self.image_edit(frame)
        q_image = QtGui.QImage(frame.data, self.width, self.height,
                               bytesPerLine, format)

        if format == QtGui.QImage.Format_RGB888:
            # OpenCV returns images as 24bit BGR (and not RGB), but there is no
            # direct support for this format in QImage
            q_image = q_image.rgbSwapped()

        self.imageLabel.setPixmap(QtGui.QPixmap.fromImage(q_image))

