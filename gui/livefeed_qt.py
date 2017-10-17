from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
import traceback

from devices.camera.umanagercamera import Lumenera

__all__ = ['LiveFeedQt']

def draw_cross(pixmap):
    painter = QtGui.QPainter(pixmap)
    pen = QtGui.QPen(QtGui.QColor(200, 0, 0))
    pen.setWidth(2)
    painter.setPen(pen)
    c_x, c_y = pixmap.width()/2, pixmap.height()/2
    painter.drawLine(c_x - 10, c_y, c_x + 10, c_y)
    painter.drawLine(c_x, c_y - 10, c_x, c_y + 10)
    painter.end()


class LiveFeedQt(QtWidgets.QLabel):
    def __init__(self, camera, mouse_callback=None,
                 image_edit=lambda frame: frame,
                 display_edit=draw_cross):
        super(LiveFeedQt, self).__init__()
        # The image_edit function (does nothing by default) gets the raw
        # unscaled image (i.e. a numpy array), while the display_edit
        # function gets a QPixmap and is meant to draw GUI elements in
        # "display space" (by default, a red cross in the middle of the
        # screen).
        self.image_edit = image_edit
        self.display_edit = display_edit
        self.camera = camera
        self.width, self.height = self.camera.width, self.camera.height
        self.callback = mouse_callback

        self.update_image()

        self.setMinimumSize(640, 480)
        self.setAlignment(Qt.AlignCenter)
        #self.setSizePolicy(QtWidgets.QSizePolicy.Minimum)

        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_image)
        timer.start(50) #20 Hz

    def mousePressEvent(self, event):
        if self.callback is not None:
            self.callback(event)

    @QtCore.pyqtSlot()
    def update_image(self):
        try:
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

            pixmap = QtGui.QPixmap.fromImage(q_image)
            size = self.size()
            width, height = size.width(), size.height()
            scaled_pixmap = pixmap.scaled(width, height,
                                         Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if self.display_edit is not None:
                self.display_edit(scaled_pixmap)
            self.setPixmap(scaled_pixmap)

        except Exception:
            print(traceback.format_exc())
