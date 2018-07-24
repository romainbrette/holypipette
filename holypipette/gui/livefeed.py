from __future__ import print_function
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

import traceback
import numpy as np


__all__ = ['LiveFeedQt']


class LiveFeedQt(QtWidgets.QLabel):
    def __init__(self, camera, image_edit=None, display_edit=None,
                 mouse_handler=None, parent=None):
        super(LiveFeedQt, self).__init__(parent=parent)
        # The image_edit function (does nothing by default) gets the raw
        # unscaled image (i.e. a numpy array), while the display_edit
        # function gets a QPixmap and is meant to draw GUI elements in
        # "display space" (by default, a red cross in the middle of the
        # screen).
        if image_edit is None:
            image_edit = lambda frame: frame
        self.image_edit = image_edit

        if display_edit is None:
            display_edit = lambda img: img
        self.display_edit = display_edit

        self.mouse_handler = mouse_handler
        self.camera = camera
        self.width, self.height = self.camera.width, self.camera.height

        self.update_image()

        self.setMinimumSize(640, 480)
        self.setAlignment(Qt.AlignCenter)

        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_image)
        timer.start(50) #20 Hz

    def mousePressEvent(self, event):
        # Ignore clicks that are not on the image
        xs = event.x() - self.size().width()/2.0
        ys = event.y() - self.size().height()/2.0
        pixmap = self.pixmap()
        if abs(xs) > pixmap.width()/2.0 or abs(ys) > pixmap.height()/2.0:
            self.setFocus()
            return

        if self.mouse_handler is not None:
            self.mouse_handler(event)

    @QtCore.pyqtSlot()
    def update_image(self):
        try:
            if not self.camera.new_frame():
                return
            # get data and display
            frame = self.camera.snap()
            if len(frame.shape) == 2:
                # Grayscale image via MicroManager
                if frame.dtype == np.dtype('uint32'):
                    bytesPerLine = self.width*4
                    format = QtGui.QImage.Format_RGB32
                else:
                    bytesPerLine = self.width
                    format = QtGui.QImage.Format_Indexed8

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

            pixmap = QtGui.QPixmap.fromImage(q_image)
            size = self.size()
            width, height = size.width(), size.height()
            scaled_pixmap = pixmap.scaled(width, height,
                                          Qt.KeepAspectRatio,
                                          Qt.SmoothTransformation)
            if self.display_edit is not None:
                self.display_edit(scaled_pixmap)
            self.setPixmap(scaled_pixmap)

        except Exception:
            print(traceback.format_exc())
