# coding=utf-8
from __future__ import absolute_import

import collections
import functools
import logging
import datetime
import traceback

import param
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt

from holypipette.controller import Command

# Add a cross to the display
from holypipette.controller.patch import NumberWithUnit


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


class Logger(QtCore.QAbstractTableModel, logging.Handler):
    def __init__(self):
        super(Logger, self).__init__()
        # We do not actually use the formatter, but the asctime attribute is
        # available if the formatter requires it
        self.setFormatter(logging.Formatter('%(asctime)s'))
        self.messages = []

    def emit(self, record):
        self.format(record)
        entry = (record.levelno,
                 datetime.datetime.strptime(record.asctime, '%Y-%m-%d %H:%M:%S,%f'),
                 record.name,
                 record.message,
                 record.exc_info,
                 record.thread)  # Not displayed by default
        self.beginInsertRows(QtCore.QModelIndex(),
                             len(self.messages), len(self.messages))
        self.messages.append(entry)
        self.endInsertRows()

    def rowCount(self, parent=None):
        return len(self.messages)

    def columnCount(self, parent=None):
        return 4

    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return
        if orientation == Qt.Horizontal:
            return ['', 'time', 'origin', 'message'][section]

    def data(self, index, role):
        if not index.isValid():
            return None
        if index.row() >= len(self.messages) or index.row() < 0:
            return None

        level, asctime, name, message, exc_info, _ = self.messages[index.row()]
        if role == Qt.DisplayRole or role == Qt.ToolTipRole:
            if index.column() == 0:
                if level == logging.DEBUG:
                    return 'D'
                elif level == logging.INFO:
                    return 'I'
                elif level == logging.WARN:
                    return 'W'
                elif level == logging.ERROR:
                    return 'E'
                else:
                    return None
            elif index.column() == 1:
                return asctime.strftime('%H:%M:%S,%f')[:-3]  # ms instead of us
            elif index.column() == 2:
                return name
            elif index.column() == 3:
                if role == Qt.DisplayRole:
                    return message
                else:
                    if exc_info is None:
                        return message
                    else:
                        return message + '\n' + ''.join(traceback.format_exception(*exc_info))
            else:
                return None
        if role == Qt.ForegroundRole:
            if level == logging.WARN:
                return QtGui.QColor('darkorange')
            elif level == logging.ERROR:
                return QtGui.QColor('darkred')

    def save_to_file(self, filename):
        with open(filename, 'w') as f:
            for entry in self.messages:
                level, asctime, name, message, exc_info, thread = entry
                fmt = '{level} {time} {origin} {thread_id}: {message}\n'
                level_name = {logging.DEBUG: 'DEBUG',
                             logging.INFO: 'INFO',
                             logging.WARN: 'WARN',
                             logging.ERROR: 'ERROR'}[level]
                if exc_info is not None:
                    message += '\n' + ''.join(traceback.format_exception(*exc_info))
                f.write(fmt.format(level=level_name,
                                   time=asctime.isoformat(' '),
                                   origin=name,
                                   thread_id=thread,
                                   message=message))

class LogViewerWindow(QtWidgets.QMainWindow):
    close_signal = QtCore.pyqtSignal()
    levels = collections.OrderedDict([('DEBUG',logging.DEBUG),
                                      ('INFO', logging.INFO),
                                      ('WARN', logging.WARN),
                                      ('ERROR', logging.ERROR)])

    def __init__(self, parent):
        super(LogViewerWindow, self).__init__(parent=parent)
        self.setWindowTitle('Log')
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        # self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.log_view = QtWidgets.QTableView()
        self.logger = Logger()
        self.log_view.setModel(self.logger)
        self.log_view.horizontalHeader().setStretchLastSection(True)
        self.log_view.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        # self.log_view.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.log_view.setShowGrid(False)
        self.log_view.setAlternatingRowColors(True)
        self.logger.rowsInserted.connect(self.log_view.scrollToBottom)
        logging.getLogger().addHandler(self.logger)
        logging.getLogger().setLevel(logging.DEBUG)
        self.current_levelno = logging.DEBUG
        central_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self.level_selection = QtWidgets.QComboBox()
        self.level_selection.insertItems(0, self.levels.keys())
        self.level_selection.currentIndexChanged.connect(self.set_level)
        top_row = QtWidgets.QHBoxLayout()
        top_row.addWidget(self.level_selection)
        self.save_button = QtWidgets.QToolButton(clicked=self.save_log)
        self.save_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton))
        top_row.addWidget(self.save_button)
        layout.addLayout(top_row)
        layout.addWidget(self.log_view)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def closeEvent(self, event):
        self.close_signal.emit()
        super(LogViewerWindow, self).closeEvent(event)

    def set_level(self, level_idx):
        levelno = self.levels.values()[level_idx]
        if self.current_levelno == levelno:
            return
        for row in range(self.logger.rowCount()):
            if self.logger.messages[row][0] >= levelno:
                self.log_view.showRow(row)
            else:
                self.log_view.hideRow(row)
        self.current_levelno = levelno

    def save_log(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Log File',
                                                            filter='Text files(*.txt)')
        if not filename:
            return
        try:
            self.logger.save_to_file(filename)
        except (OSError, IOError):
            logging.getLogger(__name__).exception('Saving log file to "{}" '
                                                  'failed.'.format(filename))

class KeyboardHelpWindow(QtWidgets.QMainWindow):

    close_signal = QtCore.pyqtSignal()

    def __init__(self, parent):
        super(KeyboardHelpWindow, self).__init__(parent=parent)
        self.setWindowTitle('Keyboard/mouse commands')
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.label = QtWidgets.QLabel()
        self.setCentralWidget(self.label)
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
                    key_text = QtGui.QKeySequence(int(modifier)).toString()
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

        self.label.setText(text)

    def _format_action(self, action, description):
        lines = ['<tr>',
                 '<td style="font-family: monospace; font-weight: bold; align: center; padding-right: 1ex">{}</td>'
                 '<td>{}</td>'.format(action, description),
                 '</tr>']
        return lines

    def closeEvent(self, event):
        self.close_signal.emit()
        super(KeyboardHelpWindow, self).closeEvent(event)


class LogNotifyHandler(logging.Handler):
    def __init__(self, signal):
        super(LogNotifyHandler, self).__init__()
        self.signal = signal

    def emit(self, record):
        self.format(record)
        if record.exc_info is None:
            message = record.msg
        else:
            _, exc, _ = record.exc_info
            message = '{} ({})'.format(record.msg, str(exc))
        self.signal.emit(message)


class BaseGui(QtWidgets.QMainWindow):
    log_signal = QtCore.pyqtSignal('QString')

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
        self.help_button = QtWidgets.QToolButton(clicked=self.toggle_help)
        self.help_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxQuestion))
        self.help_button.setCheckable(True)
        self.log_button = QtWidgets.QToolButton(clicked=self.toggle_log)
        self.log_button.setText('L')
        self.log_button.setCheckable(True)
        self.status_bar.addPermanentWidget(self.help_button)
        self.status_bar.addPermanentWidget(self.log_button)
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)
        self.status_messages = collections.OrderedDict()
        self.key_actions = {}
        self.mouse_actions = {}
        self.help_window = KeyboardHelpWindow(self)
        self.help_window.setFocusPolicy(Qt.NoFocus)
        self.help_window.setVisible(False)
        self.help_window.close_signal.connect(lambda: self.help_button.setChecked(False))
        self.log_window = LogViewerWindow(self)
        self.log_window.setFocusPolicy(Qt.NoFocus)
        self.log_window.close_signal.connect(lambda: self.log_button.setChecked(False))
        self.running_task = None
        self.running_task_controller = None

        # Display error messages directly in the status bar
        handler = LogNotifyHandler(self.log_signal)
        handler.setLevel(logging.ERROR)
        logging.getLogger('holypipette').addHandler(handler)
        self.log_signal.connect(self.error_status)

    @QtCore.pyqtSlot('QString')
    def error_status(self, message):
        self.status_bar.showMessage(message, 5000)

    def initialize(self):
        for controller, (command_signal, reset_signal) in self.controller_signals.items():
            command_signal.connect(controller.command_received)
            reset_signal.connect(controller.reset_requested)
            controller.task_finished.connect(self.task_finished)
        self.register_commands()

    def register_commands(self):
        help = Command('help', 'General', 'Toggle display of keyboard/mouse commands')
        self.register_key_action(Qt.Key_Question, None, help,
                                 func=lambda arg: self.help_button.click())
        logger = Command('log', 'General', 'Toggle display of log output')
        self.register_key_action(Qt.Key_L, None, logger,
                                 func=lambda arg: self.log_button.click())
        exit = Command('exit', 'General', 'Exit the application')
        self.register_key_action(Qt.Key_Escape, None, exit,
                                 func=lambda arg: self.close())

    def register_key_action(self, key, modifier, command, argument=None,
                            func=None, default_doc=True):
        self.key_actions[(key, modifier)] = (command, argument, func)
        if default_doc:
            self.help_window.register_key_action(key, modifier,
                                                 command.category,
                                                 command.auto_description(argument))

    def start_task(self, task_name, controller):
        self.status_bar.clearMessage()
        self.task_progress_text.setText(task_name + '…')
        self.task_progress.setVisible(True)
        self.task_abort_button.setEnabled(True)
        self.task_abort_button.setVisible(True)
        self.running_task = task_name
        self.running_task_controller = controller

    def abort_task(self):
        self.task_abort_button.setEnabled(False)
        self.running_task_controller.abort_task()

    @QtCore.pyqtSlot(int, object)
    def task_finished(self, exit_reason, executor):
        if self.running_task is None:
            return  # Nothing to do

        self.task_progress.setVisible(False)
        self.task_abort_button.setVisible(False)
        # 0: correct execution (no need to show a message)
        # 1: an error occurred (error will be displayed via `error_status`)
        if exit_reason == 2:
            text = "Task '{}' aborted.".format(self.running_task)
            self.status_bar.showMessage(text, 5000)

        # If the task was aborted or failed, and the "executor" object has a
        # saved state (e.g. the position of the pipette), ask the user whether
        # they want to reset the state
        if exit_reason != 0 and executor is not None and executor.has_saved_state():
            reply = QtWidgets.QMessageBox.question(self, "Reset",
                                                   executor.saved_state_question,
                                                   QtWidgets.QMessageBox.Yes |
                                                   QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                _, reset_signal = self.controller_signals[self.running_task_controller]
                reset_signal.emit(executor)

        self.running_task = None
        self.running_task_controller = None

    def keyPressEvent(self, event):
        # Look for an exact match first (key + modifier)
        event_tuple = (event.key(), int(event.modifiers()))
        description = self.key_actions.get(event_tuple, None)
        # If not found, check for keys that ignore the modifier
        if description is None:
            description = self.key_actions.get((event.key(), None), None)

        if description is not None:
            command, argument, func = description
            if self.running_task and not command.category == 'General':
                # Another task is running, ignore the key press
                # (we allow the "General" category to still allow to see the
                # help, etc.)
                return
            if command.task_description is not None:
                self.start_task(command.task_description, command.controller)
            if command.controller in self.controller_signals:
                command_signal, _ = self.controller_signals[command.controller]
                command_signal.emit(command.name, argument)
            elif func is not None:
                func(argument)
            else:
                raise AssertionError('Need a controller or a function')

    def toggle_help(self):
        if self.help_button.isChecked():
            self.help_window.show()
            # We need to keep the focus
            self.setFocus()
        else:
            self.help_window.setVisible(False)

    def toggle_log(self):
        if self.log_button.isChecked():
            self.log_window.setVisible(True)
            # We need to keep the focus
            self.setFocus()
        else:
            self.log_window.setVisible(False)

    @QtCore.pyqtSlot('QString', 'QString')
    def set_status_message(self, category, message):
        if message is None and category in self.status_messages:
            del self.status_messages[category]
        else:
            self.status_messages[category] = message

        messages = ' | '.join(self.status_messages.values())
        self.status_label.setText(messages)


class ConfigGui(QtWidgets.QWidget):
    def __init__(self, config):
        super(ConfigGui, self).__init__()
        self.config = config
        layout = QtWidgets.QVBoxLayout()
        self.title = QtWidgets.QLabel(config.name)
        self.title.setStyleSheet('font-weight: bold;')
        layout.addWidget(self.title)
        all_params = config.params()
        for category, params in config.categories:
            box = QtWidgets.QGroupBox(category)
            rows = QtWidgets.QVBoxLayout()
            for param_name in params:
                param_obj = all_params[param_name]
                row = QtWidgets.QHBoxLayout()
                label = QtWidgets.QLabel(param_name)
                label.setToolTip(param_obj.doc)
                if isinstance(param_obj, param.Number):
                    value_widget = QtWidgets.QDoubleSpinBox()
                    value_widget.setMinimum(param_obj.bounds[0])
                    value_widget.setMaximum(param_obj.bounds[1])
                    value_widget.setValue(getattr(config, param_name))
                    value_widget.valueChanged.connect(functools.partial(self.set_numerical_value, param_name))
                if isinstance(param_obj, NumberWithUnit):
                    value_widget = QtWidgets.QDoubleSpinBox()
                    magnitude = param_obj.magnitude
                    value_widget.setMinimum(param_obj.bounds[0]/magnitude)
                    value_widget.setMaximum(param_obj.bounds[1]/magnitude)
                    value_widget.setValue(getattr(config, param_name)/magnitude)
                    value_widget.valueChanged.connect(
                        functools.partial(self.set_numerical_value_with_unit, param_name, magnitude))
                elif isinstance(param_obj, param.Boolean):
                    value_widget = QtWidgets.QCheckBox()
                    value_widget.setChecked(getattr(config, param_name))
                    value_widget.stateChanged.connect(functools.partial(self.set_boolean_value, param_name, value_widget))
                value_widget.setToolTip(param_obj.doc)
                row.addWidget(label, stretch=1)
                row.addWidget(value_widget)
                if isinstance(param_obj, NumberWithUnit):
                    unit_label = QtWidgets.QLabel(param_obj.unit)
                    row.addWidget(unit_label)
                rows.addLayout(row)
            box.setLayout(rows)
            layout.addWidget(box)
        self.setLayout(layout)

    def set_numerical_value(self, name, value):
        setattr(self.config, name, value)

    def set_numerical_value_with_unit(self, name, magnitude, value):
        setattr(self.config, name, value*magnitude)

    def set_boolean_value(self, name, widget):
        setattr(self.config, name, widget.isChecked())