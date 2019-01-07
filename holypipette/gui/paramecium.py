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


# Helper functions for drawing
def create_painter(pixmap, color, width=1):
    """
    Setup a ``QPainter`` with a `QPen` of a given color and width.

    Parameters
    ----------
    pixmap : `.QPixMap`
        The pixmap on which to draw.
    color : tuple
        The 4-element tuple defining the color (R, G, B, alpha).
    width : int
        The width in pixels.

    Returns
    -------
    painter : `~.QtGui.QPainter`
        The painter that can be used for drawing on the pixmap.
    """
    painter = QtGui.QPainter(pixmap)
    pen = QtGui.QPen(QtGui.QColor(*color))
    pen.setWidth(width)
    painter.setPen(pen)
    return painter


def draw_contour(contour, painter, scale):
    path = QtGui.QPainterPath(QtCore.QPoint(*contour[0][0]) / scale)
    for point in contour[1:]:
        path.lineTo(QtCore.QPoint(*point[0]) / scale)
    painter.drawPath(path)


def draw_ellipse(painter, x, y, width, height, angle, pixel_per_um,
                 scale):
    width *= pixel_per_um / scale
    height *= pixel_per_um / scale
    rotate_by = angle * 180 / np.pi
    painter.translate(x / scale, y / scale)
    painter.rotate(rotate_by)
    painter.drawEllipse(-width / 2, -height / 2, width, height)
    painter.drawPoint(0, 0)
    painter.rotate(-rotate_by)
    painter.translate(-x / scale, -y / scale)


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
        #self.display_edit_funcs.append(self.show_tip)
        self.paramecium_position = (None, None, None, None, None)
        self.paramecium_interface.moveToThread(pipette_interface.thread())
        self.interface_signals[self.paramecium_interface] = (self.paramecium_command_signal,
                                                             self.paramecium_reset_signal)
        self.setWindowTitle("Paramecium GUI")
        self.add_config_gui(self.paramecium_interface.config)

    def register_commands(self):
        super(ParameciumGui, self).register_commands(manipulator_keys = False)

        self.register_mouse_action(Qt.LeftButton, Qt.ShiftModifier,
                                   self.paramecium_interface.move_pipette_floor)
        self.register_mouse_action(Qt.LeftButton, Qt.ControlModifier,
                                   self.paramecium_interface.move_pipette_working_level)
        self.register_mouse_action(Qt.RightButton, Qt.ShiftModifier,
                                   self.paramecium_interface.start_tracking)
        self.register_mouse_action(Qt.RightButton, Qt.ControlModifier,
                                   self.paramecium_interface.autofocus)
        self.register_key_action(Qt.Key_Space, None,
                                 self.paramecium_interface.move_pipette_down)
        self.register_key_action(Qt.Key_T, None,
                                 self.paramecium_interface.toggle_tracking)
        self.register_key_action(Qt.Key_Return, None,
                                 self.paramecium_interface.toggle_following)
        self.register_key_action(Qt.Key_P, None,
                                 self.paramecium_interface.display_z_manipulator)
        self.register_key_action(Qt.Key_K, None,
                                 self.paramecium_interface.automatic_experiment)
        self.register_key_action(Qt.Key_N, None,
                                 self.paramecium_interface.detect_contact)
        self.register_key_action(Qt.Key_U, None,
                                 self.paramecium_interface.focus)
        self.register_key_action(Qt.Key_B, None,
                                 self.paramecium_interface.autofocus_paramecium)
        self.register_key_action(Qt.Key_V, None,
                                 self.paramecium_interface.move_pipettes_paramecium)

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
        painter = create_painter(pixmap, color=(0, 0, 200, 125), width=3)
        x, y, width, height, angle = interface.paramecium_position
        draw_ellipse(painter, x, y, width, height, angle, pixel_per_um, scale)
        painter.end()

        if interface.config.draw_fitted_ellipses:
            painter = create_painter(pixmap, color=(0, 200, 200, 125), width=2)
            for ellipse in interface.paramecium_info['all_ellipses']:
                x, y, width, height, angle = ellipse
                draw_ellipse(painter, x, y, width, height, angle, pixel_per_um,
                             scale)
            painter.end()
            painter = create_painter(pixmap, color=(200, 0, 200, 125), width=2)
            for ellipse in interface.paramecium_info['good_ellipses']:
                x, y, width, height, angle = ellipse
                draw_ellipse(painter, x, y, width, height, angle, pixel_per_um,
                             scale)
            painter.end()

        if interface.config.draw_contours:
            # Draw all contours
            painter = create_painter(pixmap, color=(200, 200, 0, 125))
            for contour in interface.paramecium_info['all_contours']:
                draw_contour(contour, painter, scale)
            painter.end()

            # Draw unused contours that were long enough/had enough points
            painter = create_painter(pixmap, color=(200, 0, 0, 125))
            for contour in interface.paramecium_info['valid_contours']:
                draw_contour(contour, painter, scale)
            painter.end()

            # Draw best contour
            contour = interface.paramecium_info['best_contour']
            if contour is not None:
                painter = create_painter(pixmap, color=(0, 200, 0, 125),
                                         width=2)
                draw_contour(contour, painter, scale)
                painter.end()

    def show_tip(self, pixmap):
        # Show the tip of the electrode
        interface = self.paramecium_interface
        scale = 1.0 * self.camera.width / pixmap.size().width()
        pixel_per_um = getattr(self.camera, 'pixel_per_um', None)
        if pixel_per_um is None:
            pixel_per_um = interface.calibrated_unit.stage.pixel_per_um()[0]
        painter = QtGui.QPainter(pixmap)
        pen = QtGui.QPen(QtGui.QColor(0, 0, 200, 125))
        pen.setWidth(3)
        painter.setPen(pen)

        x, y, _ = interface.calibrated_unit.reference_position()
        x+=self.camera.width/2
        y+=self.camera.height/2
        width = 20 * pixel_per_um / scale
        height = 20 * pixel_per_um / scale
        painter.translate(x / scale, y / scale)

        painter.drawRect(-width / 2, -height / 2, width, height)
        painter.end()
