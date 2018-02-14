'''
This GUI only shows the camera image, without any additional controls (stage,
manipulators, pressure controller, etc.)
'''
import collections
import inspect
import signal
import sys
from os.path import expanduser

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

from gui import *


home = expanduser("~")
config_filename = home+'/config_manipulator.cfg'

# Catch segmentation faults and aborts
def signal_handler(signum, frame):
    print("*** Received signal %d" % signum)
    print("*** Frame: %s" % inspect.getframeinfo(frame))

signal.signal(signal.SIGSEGV, signal_handler)
signal.signal(signal.SIGABRT, signal_handler)


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


class CameraGui(QtWidgets.QMainWindow):

    camera_signal = QtCore.pyqtSignal('QString')

    def __init__(self, camera, image_edit, display_edit):
        super(CameraGui, self).__init__()
        self.setWindowTitle("Camera GUI")
        self.status_bar = QtWidgets.QStatusBar()
        self.status_label = QtWidgets.QLabel()
        self.status_bar.addPermanentWidget(self.status_label)
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)
        self.status_messages = collections.OrderedDict()
        self.camera = camera
        self.key_actions = {}
        self.video = LiveFeedQt(self.camera,
                                mouse_callback=self.mouse_callback,
                                image_edit=image_edit,
                                display_edit=display_edit)
        self.setCentralWidget(self.video)

        self.register_key_action(Qt.Key_Plus, None, self.camera_signal,
                                 'Camera',
                                 'increase_exposure',
                                 'Increase the exposure time by 2.5ms')
        self.register_key_action(Qt.Key_Minus, None, self.camera_signal,
                                 'Camera',
                                 'decrease_exposure',
                                 'Decrease the exposure time by 2.5ms')
        self.camera_signal.connect(self.camera.handle_command)
        self.camera.connect(self)

    def register_key_action(self, key, modifier, signal,
                            category, command, long_description):
        self.key_actions[(key, modifier)] = (signal, category, command, long_description)

    def mouse_callback(self, event):
        pass

    def keyPressEvent(self, event):
        # Look for an exact match first (key + modifier)
        event_tuple = (event.key(), event.modifiers())
        description = self.key_actions.get(event_tuple, None)
        # If not found, check for keys that ignore the modifier
        if description is None:
            description = self.key_actions.get((event.key(), None), None)

        if description is not None:
            signal, _, command, _ = description
            signal.emit(command)

    @QtCore.pyqtSlot('QString', 'QString')
    def set_status_message(self, category, message):
        if message is None and category in self.status_messages:
            del self.status_messages[category]
        else:
            self.status_messages[category] = message

        messages = ' | '.join(self.status_messages.values())
        self.status_label.setText(messages)


from setup_script import *

app = QtWidgets.QApplication(sys.argv)
gui = CameraGui(camera, image_edit=None, display_edit=draw_cross)
gui.show()
ret = app.exec_()

sys.exit(ret)
