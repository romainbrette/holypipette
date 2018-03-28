# coding=utf-8
from __future__ import absolute_import

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

from holypipette.controller.camera import CameraController
from holypipette.executor import TaskExecutor
from holypipette.gui import ConfigGui
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
    camera_reset_signal = QtCore.pyqtSignal(TaskExecutor)

    def __init__(self, camera, image_edit=None, display_edit=draw_cross):
        super(CameraGui, self).__init__()
        self.setWindowTitle("Camera GUI")
        self.camera = camera
        self.camera_controller = CameraController(camera)
        self.display_edit_funcs = [draw_cross]
        self.video = LiveFeedQt(self.camera,
                                image_edit=image_edit,
                                display_edit=self.display_edit,
                                mouse_handler=self.video_mouse_press)
        self.setFocus()  # Need this to handle arrow keys, etc.
        self.controller_signals = {self.camera_controller: (self.camera_signal,
                                                            self.camera_reset_signal)}

        # Add an (optional) area for configuration options
        self.splitter = QtWidgets.QSplitter()
        self.splitter.addWidget(self.video)
        self.config_tab = QtWidgets.QTabWidget()
        self.splitter.addWidget(self.config_tab)
        self.setCentralWidget(self.splitter)
        self.splitter.setSizes([1, 0])
        self.splitter.splitterMoved.connect(self.splitter_size_changed)

    @QtCore.pyqtSlot(int, int)
    def splitter_size_changed(self, pos, index):
        # If the splitter is moved all the way to the right, get back the focus
        if self.splitter.sizes()[1] == 0:
            self.setFocus()

    def add_config_gui(self, config):
        config_gui = ConfigGui(config)
        self.config_tab.addTab(config_gui, config.name)

    def display_edit(self, pixmap):
        for func in self.display_edit_funcs:
            func(pixmap)

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

    def register_mouse_action(self, click_type, modifier, command, func=None,
                              default_doc=True):
        self.mouse_actions[(click_type, modifier)] = (command, func)
        if default_doc:
            self.help_window.register_mouse_action(click_type, modifier,
                                                   command.category,
                                                   command.auto_description())

    def video_mouse_press(self, event):
        # Look for an exact match first (key + modifier)
        event_tuple = (event.button(), int(event.modifiers()))
        description = self.mouse_actions.get(event_tuple, None)
        # If not found, check for keys that ignore the modifier
        if description is None:
            description = self.mouse_actions.get((event.button(), None), None)

        if description is not None:
            command, func = description
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
            if command.task_description is not None:
                self.start_task(command.task_description, command.controller)
            if command.controller in self.controller_signals:
                command_signal, _ = self.controller_signals[command.controller]
                command_signal.emit(command.name, position)
            elif func is not None:
                func(position)
            else:
                raise AssertionError('Need a controller or a function')

    def toggle_configuration_display(self, arg):
        # We get arg=None as the argument, just ignore it
        current_sizes = self.splitter.sizes()
        if current_sizes[1] == 0:
            min_size = self.config_tab.sizeHint().width()
            new_sizes = [current_sizes[0]-min_size, min_size]
        else:
            new_sizes = [current_sizes[0]+current_sizes[1], 0]
            self.setFocus()
        self.splitter.setSizes(new_sizes)