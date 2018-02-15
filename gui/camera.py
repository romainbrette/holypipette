import collections

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

from .livefeed_qt import LiveFeedQt


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


class KeyboardHelpWindow(QtWidgets.QLabel):

    def __init__(self, parent):
        super(KeyboardHelpWindow, self).__init__(parent=parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                           QtWidgets.QSizePolicy.MinimumExpanding)
        self.help_catalog = collections.OrderedDict()

    def register_key_action(self, key, modifier, category, description):
        if category not in self.help_catalog:
            self.help_catalog[category] = []
        self.help_catalog[category].append((key, modifier, description))
        self.update_text()

    def update_text(self):
        lines = []
        for category, info in self.help_catalog.iteritems():
            lines.append('<tr><td colspan=2 style="font-size: large; padding-top: 1ex">{}</td></tr>'.format(category))

            for key, modifier, description in info:
                if modifier is not None:
                    key_text = QtGui.QKeySequence(int(modifier) + key).toString()
                else:
                    key_text = QtGui.QKeySequence(key).toString()

                lines.append('<tr>')
                lines.append('<td style="font-weight: bold; align: center; padding-right: 1ex">{}</td>'
                             '<td>{}</td>'.format(key_text,
                                                                           description))
                lines.append('</tr>')
        text = '<table>' +('\n'.join(lines)) + '</table>'
        self.setText(text)


class CameraGui(QtWidgets.QMainWindow):

    camera_signal = QtCore.pyqtSignal('QString', object)

    def __init__(self, camera, image_edit=None, display_edit=draw_cross):
        super(CameraGui, self).__init__()
        self.setWindowTitle("Camera GUI")
        self.status_bar = QtWidgets.QStatusBar()
        self.status_label = QtWidgets.QLabel()
        self.status_bar.addPermanentWidget(self.status_label)
        self.help_button = QtWidgets.QPushButton(clicked=self.toggle_help)
        self.help_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxQuestion))
        self.help_button.setCheckable(True)
        self.help_button.setFlat(True)
        self.status_bar.addPermanentWidget(self.help_button)
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)
        self.status_messages = collections.OrderedDict()
        self.camera = camera
        self.key_actions = {}
        self.video = LiveFeedQt(self.camera,
                                mouse_callback=self.mouse_callback,
                                image_edit=image_edit,
                                display_edit=display_edit)
        self.help_window = KeyboardHelpWindow(self.video)
        self.help_window.setAutoFillBackground(True)
        self.help_window.setStyleSheet("QLabel { background-color : rgb(200, 200, 200, 175); "
                                       "color : rgb(200, 0, 0)}")
        self.help_window.setVisible(False)
        self.help_window.setFocusPolicy(Qt.NoFocus)
        self.setCentralWidget(self.video)
        self.camera_signal.connect(self.camera.handle_command)
        self.camera.connect(self)
        self.register_commands()

    def register_commands(self):
        self.register_key_action(Qt.Key_Plus, None, self.camera_signal, None,
                                 'Camera',
                                 'increase_exposure',
                                 'Increase the exposure time by 2.5ms')
        self.register_key_action(Qt.Key_Minus, None, self.camera_signal, None,
                                 'Camera',
                                 'decrease_exposure',
                                 'Decrease the exposure time by 2.5ms')
        self.register_key_action(Qt.Key_I, None, self.camera_signal, None,
                                 'Camera',
                                 'save_image',
                                 'Save the current camera image to a file')
        self.register_key_action(Qt.Key_Question, None, lambda: self.help_button.click(), None,
                                 'General',
                                 '',
                                 'Toggle display of keyboard shortcuts')
        self.register_key_action(Qt.Key_Escape, None, self.close, None,
                                 'General',
                                 '',
                                 'Exit the application')


    def register_key_action(self, key, modifier, signal_or_func, argument,
                            category, command, long_description):
        self.key_actions[(key, modifier)] = (signal_or_func, category, command, argument, long_description)
        self.help_window.register_key_action(key, modifier, category, long_description)

    def mouse_callback(self, event):
        pass

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress:
            # Look for an exact match first (key + modifier)
            event_tuple = (event.key(), int(event.modifiers()))
            description = self.key_actions.get(event_tuple, None)
            # If not found, check for keys that ignore the modifier
            if description is None:
                description = self.key_actions.get((event.key(), None), None)

            if description is not None:
                signal_or_func, _, command, argument, _ = description
                if isinstance(signal_or_func, QtCore.pyqtBoundSignal):
                    signal_or_func.emit(command, argument)
                else:
                    signal_or_func()
                return True
        return False

    def toggle_help(self):
        self.help_window.setVisible(not self.help_window.isVisible())


    @QtCore.pyqtSlot('QString', 'QString')
    def set_status_message(self, category, message):
        if message is None and category in self.status_messages:
            del self.status_messages[category]
        else:
            self.status_messages[category] = message

        messages = ' | '.join(self.status_messages.values())
        self.status_label.setText(messages)
