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
from holypipette.gui.manipulator import ManipulatorGui

class ParameciumGui(ManipulatorGui):

    paramecium_command_signal = QtCore.pyqtSignal(MethodType, object)
    paramecium_reset_signal = QtCore.pyqtSignal(TaskController)

    def __init__(self, camera, pipette_interface):
        super(ParameciumGui, self).__init__(camera,
                                            pipette_interface=pipette_interface,
                                            with_tracking=False)
        self.paramecium_interface = ParameciumInterface(pipette_interface,
                                                        camera)
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
                                   self.paramecium_interface.move_pipette_floor)
        self.register_mouse_action(Qt.LeftButton, Qt.ControlModifier,
                                   self.paramecium_interface.move_pipette_working_level)
        self.register_mouse_action(Qt.RightButton, Qt.ShiftModifier,
                                   self.paramecium_interface.start_tracking)
        self.register_key_action(Qt.Key_Space, None,
                                 self.paramecium_interface.move_pipette_down)
        self.register_key_action(Qt.Key_T, None,
                                 self.paramecium_interface.toggle_tracking)

    def track_paramecium(self, frame):
        self.paramecium_interface.track_paramecium(frame)
        return frame

    def show_paramecium(self, pixmap):
        interface = self.paramecium_interface
        if (not interface.tracking or
                any(p is None for p in interface.paramecium_position)):
            return
        scale = 1.0 * self.camera.width / pixmap.size().width()
        pixel_per_um = getattr(self.camera, 'pixel_per_um', None)
        if pixel_per_um is None:
            pixel_per_um = interface.calibrated_unit.stage.pixel_per_um()[0]
        # print('pixel_per_um', pixel_per_um, 'scale', scale)
        painter = QtGui.QPainter(pixmap)
        pen = QtGui.QPen(QtGui.QColor(0, 0, 200, 125))
        pen.setWidth(3)
        painter.setPen(pen)
        x, y, width, height, angle = interface.paramecium_position
        width *= pixel_per_um/scale
        height *= pixel_per_um/scale
        rotate_by = angle*180/np.pi
        painter.translate(x/scale, y/scale)
        painter.rotate(rotate_by)

        painter.drawEllipse(-width/2, -height/2, width, height)
        painter.drawPoint(0, 0)
        painter.end()
