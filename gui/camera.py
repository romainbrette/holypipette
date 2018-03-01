# coding=utf-8
from __future__ import absolute_import

import collections

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

from base.controller import Command
from controller.camera import CameraController
from .livefeed import LiveFeedQt
from .base import BaseGui


# Add a cross to the display
def draw_cross(pixmap):
    '''
    Draws a cross at the center
    '''
    painter = QtGui.QPainter(pixmap)
    pen = QtGui.QPen(QtGui.QColor(200, 0, 0, 125))
    pen.setWidth(4)
    painter.setPen(pen)
    c_x, c_y = pixmap.width()/2, pixmap.height()/2
    painter.drawLine(c_x - 15, c_y, c_x + 15, c_y)
    painter.drawLine(c_x, c_y - 15, c_x, c_y + 15)
    painter.end()


class CameraGui(BaseGui):

    camera_signal = QtCore.pyqtSignal('QString', object)

    def __init__(self, camera, image_edit=None, display_edit=draw_cross):
        super(CameraGui, self).__init__()
        self.setWindowTitle("Camera GUI")
        self.camera = camera
        self.camera_controller = CameraController(camera)
        self.video = LiveFeedQt(self.camera,
                                image_edit=image_edit,
                                display_edit=display_edit)
        self.setFocus()  # Need this to handle arrow keys, etc.
        self.setCentralWidget(self.video)
        self.controller_signals = {self.camera_controller: self.camera_signal}

    def initialize(self):
        super(CameraGui, self).initialize()
        self.camera_controller.connect(self)

    def register_commands(self):
        super(CameraGui, self).register_commands()
        self.register_key_action(Qt.Key_Plus, None,
                                 self.camera_controller.commands[
                                     'increase_exposure'])
        self.register_key_action(Qt.Key_Minus, None,
                                 self.camera_controller.commands[
                                     'decrease_exposure'])
        self.register_key_action(Qt.Key_I, None,
                                 self.camera_controller.commands['save_image'])

    def close(self):
        del self.camera
        super(CameraGui, self).close()

    def mousePressEvent(self, event):
        # Look for an exact match first (key + modifier)
        event_tuple = (event.button(), int(event.modifiers()))
        description = self.mouse_actions.get(event_tuple, None)
        # If not found, check for keys that ignore the modifier
        if description is None:
            description = self.mouse_actions.get((event.button(), None), None)

        if description is not None:
            command, func, task_name = description
            if self.running_task:
                # Another task is running, ignore the mouse click
                return
            # Mouse commands do not have custom arguments, they always get
            # the position in the image (rescaled, i.e. independent of the
            # window size)
            x, y = event.x(), event.y()
            xs = x - self.video.size().width() / 2.
            ys = y - self.video.size().height() / 2.
            # displayed image is not necessarily the same size as the original camera image
            scale = 1.0 * self.camera.width / self.video.pixmap().size().width()
            position = (xs * scale, ys * scale)
            if task_name is not None:
                self.start_task(task_name, command.controller)
            if command.controller in self.controller_signals:
                signal = self.controller_signals[command.controller]
                signal.emit(command.name, position)
            elif func is not None:
                func(position)
            else:
                raise AssertionError('Need a controller or a function')
