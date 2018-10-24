'''
GUI for Paramecium electrophysiology
'''
from __future__ import absolute_import

from types import MethodType

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
import numpy as np

from holypipette.controller import TaskController
from holypipette.interface.paramecium import ParameciumInterface
from holypipette.vision.paramecium_tracking import where_is_paramecium
from holypipette.gui.manipulator import ManipulatorGui

class ParameciumGui(ManipulatorGui):

    paramecium_command_signal = QtCore.pyqtSignal(MethodType, object)
    paramecium_reset_signal = QtCore.pyqtSignal(TaskController)

    def __init__(self, camera, pipette_interface):
        super(ParameciumGui, self).__init__(camera,
                                            pipette_interface=pipette_interface,
                                            with_tracking=False)
        self.paramecium_interface = ParameciumInterface(pipette_interface)
        self.image_edit_funcs.append(self.track_paramecium)
        self.display_edit_funcs.append(self.show_paramecium)
        self.paramecium_position = (None, None, None, None, None)
        self.paramecium_interface.moveToThread(pipette_interface.thread())
        self.interface_signals[self.paramecium_interface] = (self.paramecium_command_signal,
                                                             self.paramecium_reset_signal)
        self.setWindowTitle("Paramecium GUI")
        self.add_config_gui(self.paramecium_interface.config)

    def register_commands(self):
        super(ParameciumGui, self).register_commands()

        self.register_mouse_action(Qt.LeftButton, Qt.ShiftModifier,
                                   self.paramecium_interface.move_pipette_down)

    def track_paramecium(self, frame):
        result = where_is_paramecium(frame, 1/self.camera.scale_factor,
                                     previous_x=self.paramecium_position[0],
                                     previous_y=self.paramecium_position[1],
                                     config=self.paramecium_interface.config)
        self.paramecium_position = result
        return frame

    def show_paramecium(self, pixmap):
        if self.paramecium_position[0] is None:
            return
        stage = self.interface.calibrated_stage

        scale = 1.0 * self.camera.width / pixmap.size().width()
        # print('pixel_per_um', pixel_per_um, 'scale', scale)
        painter = QtGui.QPainter(pixmap)
        pen = QtGui.QPen(QtGui.QColor(0, 0, 200, 125))
        pen.setWidth(3)
        painter.setPen(pen)
        # pos_x, pos_y = self.paramecium_position
        # pos_x *= scale
        # pos_y *= scale
        # print('position for plotting', pos_x, pos_y)
        x, y, angle, width, height = self.paramecium_position
        rotate_by = (angle - np.pi/2)*180/np.pi
        painter.translate(x / scale, y / scale)
        painter.rotate(rotate_by)
        painter.drawEllipse(-width/scale, -height/scale, 2*width/scale, 2*height/scale)
        painter.drawPoint(0, 0)
        painter.end()
