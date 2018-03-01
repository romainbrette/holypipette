# coding=utf-8
from __future__ import absolute_import

import collections

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

from base.controller import Command

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
        self.key_catalog = collections.OrderedDict()
        self.mouse_catalog = collections.OrderedDict()
        self.custom_catalog = collections.OrderedDict()

    def register_key_action(self, key, modifier, category, description):
        if category not in self.key_catalog:
            self.key_catalog[category] = []
        self.key_catalog[category].append((key, modifier, description))
        self.update_text()

    def register_mouse_action(self, click_type, modifier, category, description):
        if category not in self.mouse_catalog:
            self.mouse_catalog[category] = []
        self.mouse_catalog[category].append((click_type, modifier, description))
        self.update_text()

    def register_custom_action(self, category, action, description):
        if category not in self.custom_catalog:
            self.custom_catalog[category] = []
        self.custom_catalog[category].append((action, description))

    def update_text(self):
        lines = []
        # Keys
        for category, key_info in self.key_catalog.iteritems():
            # FIXME: The logic below assumes that there is no category that does
            # not have any standard key actions. Instead, we should build a
            # list of all categories first and then go through all catalogs.
            lines.append('<tr><td colspan=2 style="font-size: large; padding-top: 1ex">{}</td></tr>'.format(category))

            mouse_info = self.mouse_catalog.get(category, [])
            for click_type, modifier, description in mouse_info:
                if modifier is not None and modifier != Qt.NoModifier:
                    key_text = QtGui.QKeySequence(int(modifier)).toString() + '+'
                else:
                    key_text = ''
                if click_type == Qt.LeftButton:
                    mouse_text = 'Left click'
                elif click_type == Qt.RightButton:
                    mouse_text = 'Right click'
                elif click_type == Qt.MiddleButton:
                    mouse_text = 'Middle click'
                else:
                    mouse_text = '??? click'
                action = key_text + mouse_text
                lines.extend(self._format_action(action, description))

            custom_info = self.custom_catalog.get(category, [])
            for action, description in custom_info:
                lines.extend(self._format_action(action, description))

            for key, modifier, description in key_info:
                if modifier is not None:
                    key_text = QtGui.QKeySequence(int(modifier) + key).toString()
                else:
                    key_text = QtGui.QKeySequence(key).toString()

                lines.extend(self._format_action(key_text, description))
        text = '<table>' +('\n'.join(lines)) + '</table>'

        self.setText(text)

    def _format_action(self, action, description):
        lines = ['<tr>',
                 '<td style="font-family: monospace; font-weight: bold; align: center; padding-right: 1ex">{}</td>'
                 '<td>{}</td>'.format(action, description),
                 '</tr>']
        return lines


class BaseGui(QtWidgets.QMainWindow):
    def __init__(self):
        super(BaseGui, self).__init__()
        self.status_bar = QtWidgets.QStatusBar()
        self.task_abort_button = QtWidgets.QPushButton(clicked=self.abort_task)
        self.task_abort_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogCancelButton))
        self.task_abort_button.setVisible(False)
        self.status_bar.addWidget(self.task_abort_button)
        self.task_progress = QtWidgets.QProgressBar(parent=self)
        self.task_progress.setMaximum(0)
        self.task_progress.setAlignment(Qt.AlignLeft)
        self.task_progress.setTextVisible(False)
        self.task_progress.setVisible(False)
        layout = QtWidgets.QHBoxLayout(self.task_progress)
        self.task_progress_text = QtWidgets.QLabel()
        self.task_progress_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.task_progress_text)
        layout.setContentsMargins(0, 0, 0, 0)
        self.status_bar.addWidget(self.task_progress, 1)
        self.status_label = QtWidgets.QLabel()
        self.status_bar.addPermanentWidget(self.status_label)
        self.help_button = QtWidgets.QPushButton(clicked=self.toggle_help)
        self.help_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxQuestion))
        self.help_button.setCheckable(True)
        self.status_bar.addPermanentWidget(self.help_button)
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)
        self.status_messages = collections.OrderedDict()
        self.key_actions = {}
        self.mouse_actions = {}
        self.help_window = KeyboardHelpWindow(self)
        self.help_window.setAutoFillBackground(True)
        self.help_window.setStyleSheet("QLabel { background-color : rgb(200, 200, 200, 175); "
                                       "color : rgb(200, 0, 0)}")
        self.help_window.setVisible(False)
        self.help_window.setFocusPolicy(Qt.NoFocus)
        self.running_task = None

    def initialize(self):
        for controller, signal in self.controller_signals.items():
            signal.connect(controller.command_received)
        self.register_commands()

    def register_commands(self):
        help = Command('help', 'General', 'Toggle display of keyboard/mouse commands')
        self.register_key_action(Qt.Key_Question, None, help,
                                 func=lambda arg: self.help_button.click())
        exit = Command('exit', 'General', 'Exit the application')
        self.register_key_action(Qt.Key_Escape, None, exit,
                                 func=lambda arg: self.close())

    def register_key_action(self, key, modifier, command, argument=None,
                            func=None, task_name=None, default_doc=True):
        self.key_actions[(key, modifier)] = (command, argument, func, task_name)
        if default_doc:
            self.help_window.register_key_action(key, modifier,
                                                 command.category,
                                                 command.auto_description(argument))

    def register_mouse_action(self, click_type, modifier, command, func=None,
                              task_name=None, default_doc=True):
        self.mouse_actions[(click_type, modifier)] = (command, func, task_name)
        if default_doc:
            self.help_window.register_mouse_action(click_type, modifier,
                                                   command.category,
                                                   command.auto_description())

    def start_task(self, task_name, controller):
        self.status_bar.clearMessage()
        self.task_progress_text.setText(task_name + '…')
        self.task_progress.setVisible(True)
        self.task_abort_button.setVisible(True)
        self.running_task = task_name
        self.running_task_controller = controller

    def abort_task(self):
        self.running_task_controller.abort_task()

    @QtCore.pyqtSlot(int)
    def task_finished(self, exit_reason):
        # 0 = normal exit, 1 = error, 2 = abort
        self.task_progress.setVisible(False)
        self.task_abort_button.setVisible(False)
        if exit_reason == 0:
            text = "Task '{}' finished successfully.".format(self.running_task)
        elif exit_reason == 1:
            text = "Task '{}' failed (see log for details).".format(self.running_task)
        elif exit_reason == 2:
            text = "Task '{}' aborted.".format(self.running_task)
        else:
            #TODO Warning
            text = "Task {} ended for unknown reason".format(self.running_task)
        self.status_bar.showMessage(text, 5000)
        self.running_task = None

    def keyPressEvent(self, event):
        # Look for an exact match first (key + modifier)
        event_tuple = (event.key(), int(event.modifiers()))
        description = self.key_actions.get(event_tuple, None)
        # If not found, check for keys that ignore the modifier
        if description is None:
            description = self.key_actions.get((event.key(), None), None)

        if description is not None:
            command, argument, func, task_name = description
            if self.running_task:
                # Another task is running, ignore the key press
                return
            if task_name is not None:
                self.start_task(task_name, command.controller)
            if command.controller in self.controller_signals:
                signal = self.controller_signals[command.controller]
                signal.emit(command.name, argument)
            elif func is not None:
                func(argument)
            else:
                raise AssertionError('Need a controller or a function')

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
