from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

__all__ = ['LiveFeedQt']

def insert_cross(image):
    width, height = image.shape[:2]
    image[width//2-10:width//2+10, height//2, :] = (0, 0, 200)
    image[width//2, height//2-10:height//2+10, :] = (0, 0, 200)
    return image


class ClickableLabel(QtWidgets.QLabel):
    def __init__(self, callback=None):
        self.callback = callback
        super(ClickableLabel, self).__init__()

    def mousePressEvent(self, event):
        if self.callback is not None:
            self.callback(event)


class LiveFeedQt(QtWidgets.QMainWindow):
    def __init__(self, camera, mouse_callback=None, image_edit=insert_cross):
        super(LiveFeedQt, self).__init__()
        self.image_edit = image_edit

        self.camera = camera
        self.width, self.height = camera.width, self.camera.height
        self.imageLabel = ClickableLabel(mouse_callback)


        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidget(self.imageLabel)
        self.setCentralWidget(self.scrollArea)

        self.setWindowTitle("Camera")

        self.update_image()
        self.imageLabel.adjustSize()

        self.resize(self.imageLabel.sizeHint())

        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_image)
        timer.start(33) #30 Hz

    def update_image(self):
        # get data and display
        frame = self.image_edit(self.camera.snap())
        bytesPerLine = 3 * self.width
        format = QtGui.QImage.Format_RGB888

        q_image = QtGui.QImage(frame.data, self.width, self.height,
                               bytesPerLine, format)
        # OpenCV returns images as 24bit BGR (and not RGB), but there is no
        # direct support for this format in QImage
        q_image = q_image.rgbSwapped()

        self.imageLabel.setPixmap(QtGui.QPixmap.fromImage(q_image))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


if __name__ == '__main__':
    from devices.camera.opencvcamera import OpenCVCamera
    import sys

    # Example of using this camera live feed as a standalone program together
    # with a callback that receives mouse click events
    def my_callback(event):
        if event.button() == Qt.LeftButton:
            button = 'Left'
        elif event.button() == Qt.MiddleButton:
            button = 'Middle'
        elif event.button() == Qt.RightButton:
            button = 'Right'
        else:
            button = 'Unknown'
        print('{} button: ({}, {})'.format(button, event.x(), event.y()))

    app = QtWidgets.QApplication(sys.argv)
    camera = OpenCVCamera()
    viewer = LiveFeedQt(camera, callback=my_callback)
    viewer.show()
    sys.exit(app.exec_())
