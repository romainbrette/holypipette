# coding=utf-8
from __future__ import absolute_import

import collections
import functools
import logging
import datetime
import traceback
from types import MethodType

import param
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt
import qtawesome as qta


from holypipette.controller import TaskController
from holypipette.interface.patch import NumberWithUnit
from holypipette.interface.base import command, TaskInterface, blocking_command, command
from .livefeed import LiveFeedQt


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
        self.save_button.setIcon(qta.icon('fa.download'))
        top_row.addWidget(self.save_button)
        layout.addLayout(top_row)
        layout.addWidget(self.log_view)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def closeEvent(self, event):
        self.close_signal.emit()
        super(LogViewerWindow, self).closeEvent(event)

    def set_level(self, level_idx):
        levelno = list(self.levels.values())[level_idx]
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
                                                            filter='Text files(*.txt)',
                                                            options=QtWidgets.QFileDialog.DontUseNativeDialog)
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

    def keyPressEvent(self, event):
        # Forward key presses to the parent window
        return self.parent().keyPressEvent(event)

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
        for category, key_info in self.key_catalog.items():
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


class CameraInterface(TaskInterface):

    def __init__(self, camera):
        super(CameraInterface, self).__init__()
        self.thread = QtCore.QThread()
        self.moveToThread(self.thread)
        self.thread.start()
        self.camera = camera

    def link_signal(self, controller, method_name , signal):
        _orig_method = getattr(controller, method_name)
        def wrapper(self, *args, **kwds):
            ret_val = _orig_method(*args, **kwds)
            signal.emit(ret_val)
            return ret_val
        setattr(controller, method_name, MethodType(wrapper, controller))

    def execute(self, *args, **kwds):
        print('in CameraInterface.execute')
        return super().execute(*args, **kwds)


class SimpleCameraGui(QtWidgets.QMainWindow):
    '''
    The basic GUI for showing a camera image.

    Parameters
    ----------
    camera : `.Camera`
        The `.Camera` object that will be used for displaying an image via
        `.LiveFeedQt`.
    image_edit : function or list of functions, optional
        A function that will be called with the numpy array returned by the
        camera. Can be used to post-process the image, e.g. to change its
        brightness.
    display_edit : function or list of functions, optional
        A function that will be called with the `.QPixmap` that is based on
        the camera image. Can be used to display additional information on top
        of this image, e.g. a scale bar or text.
    with_tracking : bool, optional
        Whether to activate the object tracking interface. Defaults to
        ``False``.
    '''
    log_signal = QtCore.pyqtSignal('QString')
    camera_signal = QtCore.pyqtSignal(MethodType, object)
    camera_reset_signal = QtCore.pyqtSignal(TaskController)
    updated_exposure_signal = QtCore.pyqtSignal(float)

    # Add a cross to the display
    def draw_cross(self, pixmap):
        '''
        Draws a cross at the center. Meant to be used as a ``display_edit``
        function.

        Parameters
        ----------
        pixmap : `QPixmap`
            The pixmap to draw on.
        '''
        painter = QtGui.QPainter(pixmap)
        pen = QtGui.QPen(QtGui.QColor(200, 0, 0, 125))
        pen.setWidth(4)
        painter.setPen(pen)
        c_x, c_y = pixmap.width() / 2, pixmap.height() / 2
        painter.drawLine(c_x - 15, c_y, c_x + 15, c_y)
        painter.drawLine(c_x, c_y - 15, c_x, c_y + 15)
        painter.end()

    def __init__(self, camera, image_edit=None, display_edit=None,
                 with_tracking=False):
        super(SimpleCameraGui, self).__init__()
        self.camera = camera
        # self.camera.trigger_signal('set_exposure', self.updated_exposure_signal)
        self.interface = CameraInterface(camera)
        self.interface.link_signal(self.camera, 'set_exposure',
                                   self.updated_exposure_signal)
        self.updated_exposure_signal.connect(self.update_exposure_message)
        self.show_overlay = True
        self.with_tracking = with_tracking
        self.status_bar = QtWidgets.QStatusBar()
        self.task_abort_button = QtWidgets.QToolButton(clicked=self.abort_task)
        self.task_abort_button.setIcon(qta.icon('fa.ban'))
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
        self.help_button.setIcon(qta.icon('fa.question-circle'))
        self.help_button.setCheckable(True)

        self.flip_button = QtWidgets.QToolButton(clicked=self.camera.flip)
        self.flip_button.setIcon(qta.icon('fa.exchange'))

        self.log_button = QtWidgets.QToolButton(clicked=self.toggle_log)
        self.log_button.setIcon(qta.icon('fa.file'))
        self.log_button.setCheckable(True)

        self.autoexposure_button = QtWidgets.QToolButton(clicked=self.auto_exposure)
        self.autoexposure_button.setIcon(qta.icon('fa.camera'))

        self.status_bar.addPermanentWidget(self.help_button)
        self.status_bar.addPermanentWidget(self.log_button)
        self.status_bar.addPermanentWidget(self.flip_button)
        self.status_bar.addPermanentWidget(self.autoexposure_button)

        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)
        self.status_bar.messageChanged.connect(self.status_message_updated)
        self.status_messages = collections.OrderedDict()
        self.key_actions = {}
        self.mouse_actions = {}
        self.help_window = KeyboardHelpWindow(self)
        self.help_window.setFocusPolicy(Qt.NoFocus)
        self.help_window.setVisible(False)
        self.help_window.close_signal.connect(
            lambda: self.help_button.setChecked(False))
        self.log_window = LogViewerWindow(self)
        self.log_window.setFocusPolicy(Qt.NoFocus)
        self.log_window.close_signal.connect(
            lambda: self.log_button.setChecked(False))
        self.running_task = None
        self.running_task_interface = None
        self.config_button = None  # see initialize
        self.setWindowTitle("Camera GUI")

        self.display_edit_funcs = []
        if display_edit is None:
            display_edit = self.draw_cross
        if isinstance(display_edit, collections.Sequence):
            self.display_edit_funcs.extend(display_edit)
        else:
            self.display_edit_funcs.append(display_edit)

        self.image_edit_funcs = []
        if isinstance(image_edit, collections.Sequence):
            self.image_edit_funcs.extend(image_edit)
        elif image_edit is not None:
            self.image_edit_funcs.append(image_edit)

        self.video = LiveFeedQt(self.camera,
                                image_edit=self.image_edit,
                                display_edit=self.display_edit,
                                mouse_handler=self.video_mouse_press)
        self.setFocus()  # Need this to handle arrow keys, etc.

        self.splitter = QtWidgets.QSplitter()
        self.splitter.addWidget(self.video)
        self.config_tab = QtWidgets.QTabWidget()
        self.splitter.addWidget(self.config_tab)
        self.setCentralWidget(self.splitter)
        self.splitter.setSizes([1, 0])
        self.splitter.splitterMoved.connect(self.splitter_size_changed)

        # Display error messages directly in the status bar
        handler = LogNotifyHandler(self.log_signal)
        handler.setLevel(logging.ERROR)
        logging.getLogger('holypipette').addHandler(handler)
        self.log_signal.connect(self.error_status)

        # Display initial exposure time
        exposure = self.camera.get_exposure()
        self.updated_exposure_signal.emit(exposure)

    def display_edit(self, pixmap):
        '''
        Applies the functions stored in `~.SimpleCameraGui.display_edit_funcs` to the
        video image pixmap.

        Parameters
        ----------
        pixmap : `QPixmap`
            The pixmap to draw on.
        '''
        if self.show_overlay:
            for func in self.display_edit_funcs:
                func(pixmap)

    def image_edit(self, image):
        '''
        Applies the functions stored in `~.SimpleCameraGui.image_edit_funcs` to the
        video image. Each function works on the result of the previous function

        Parameters
        ----------
        image : `~numpy.ndarray`
            The original video image  or the image returned by a previously
            called function.

        Returns
        -------
        new_image : `~numpy.ndarray`
            The post-processed image. Should be of the same size and data type
            as the original image.
        '''
        for func in self.image_edit_funcs:
            image = func(image)
        return image

    @command(category='General',
             description='Exit the application')
    def exit(self):
        self.close()

    @blocking_command(category='Camera',
                      description='Auto exposure',
                      task_description='Adjusting exposure')
    def auto_exposure(self, *args):
        print('executing with interface')
        self.interface.execute(self.camera.auto_exposure)

    @command(category='Camera',
             description='Save the current image to a file')
    def save_image(self):
        try:
            from PIL import Image
        except ImportError:
            self.error('Saving images needs the PIL or Pillow module')
            return
        frame = self.camera.snap()
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(caption='Save image',
                                                         filter='Images (*.png, *.tiff)',
                                                         options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if len(fname):
            img = Image.fromarray(frame)
            try:
                img.save(fname)
            except (KeyError, IOError):
                self.exception('Saving image as "%s" failed.' % fname)

    def register_commands(self):
        '''
        Tie keypresses and mouse clicks to commands. Should call
        `.register_key_action` and `.register_mouse_action`. Overriding methods
        in subclass should call the superclass if they want to keep the
        commands registered by the superclass(es).
        '''
        self.register_key_action(Qt.Key_Question, None, self.help_keypress)
        self.register_key_action(Qt.Key_L, None, self.log_keypress)
        self.register_key_action(Qt.Key_Escape, None, self.exit)
        self.register_key_action(Qt.Key_Plus, None,
                                 self.camera.change_exposure,
                                 argument=2.5,
                                 default_doc=False)
        self.register_key_action(Qt.Key_Minus, None,
                                 self.camera.change_exposure,
                                 argument=-2.5,
                                 default_doc=False)
        self.help_window.register_custom_action('Camera', '+/-',
                                                'Increase/decrease exposure by 2.5ms')
        self.register_key_action(Qt.Key_I, None,
                                 self.save_image)
        self.register_key_action(Qt.Key_X, None, self.auto_exposure)

    def close(self):
        '''
        Close the GUI.
        '''
        del self.camera
        super(SimpleCameraGui, self).close()

    def register_mouse_action(self, click_type, modifier, command,
                              default_doc=True):
        '''
        Link a mouse click on the camera image to an action.

        Parameters
        ----------
        click_type : `.Qt.MouseButton`
            The type of click that should be handled as a ``Qt`` constant, e.g.
            `.Qt.LeftButton` or `.Qt.RightButton`.
        modifier : `.Qt.Modifer` or ``None``
            The modifier that needs to be pressed at the same time to trigger
            the action. The modifier needs to be given as a ``Qt`` constant,
            e.g. `.Qt.ShiftModifier` or `.Qt.ControlModifier`. Alternatively,
            ``None`` can be used to specify that the mouse click should lead to
            the action independent of the modifier.
        command : method
            A method implementing the action that has been annotated with the
            `@command <.command>` or `@blocking_command <.blocking_command>`
            decorator.
        default_doc : bool, optional
            Whether to include the action in the automatically generated help.
            Defaults to ``True``.
        '''
        self.mouse_actions[(click_type, modifier)] = command
        if default_doc:
            self.help_window.register_mouse_action(click_type, modifier,
                                                   command.category,
                                                   command.auto_description())

    def video_mouse_press(self, event):
        # Look for an exact match first (key + modifier)
        event_tuple = (event.button(), int(event.modifiers()))
        command = self.mouse_actions.get(event_tuple, None)
        # If not found, check for keys that ignore the modifier
        if command is None:
            command = self.mouse_actions.get((event.button(), None), None)

        if command is not None:
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
            if command.is_blocking:
                self.start_task(command.task_description, command.__self__)
            if command.__self__ in self.interface_signals:
                command_signal, _ = self.interface_signals[command.__self__]
                command_signal.emit(command, position)
            else:
                command(position)

    @QtCore.pyqtSlot('QString')
    def status_message_updated(self, message):
        if not message:
            self.status_bar.setStyleSheet('QStatusBar{color: black;}')

    @QtCore.pyqtSlot('QString')
    def error_status(self, message):
        self.status_bar.setStyleSheet('QStatusBar{color: red;}')
        self.status_bar.showMessage(message, 5000)

    def initialize(self):
        print('initializaing')
        self.camera_signal.connect(self.interface.command_received)
        self.camera_reset_signal.connect(self.interface.reset_requested)
        self.interface.task_finished.connect(self.task_finished)
        self.interface.connect(self)
        self.register_commands()
        # Add a button for the configuration options if necessary
        if self.config_tab.count() > 0:
            self.config_button = QtWidgets.QToolButton(
                clicked=self.toggle_configuration_display)
            self.config_button.setIcon(qta.icon('fa.cogs'))
            self.config_button.setCheckable(True)
            self.status_bar.addPermanentWidget(self.config_button)

    def register_key_action(self, key, modifier, command, argument=None,
                            default_doc=True):
        '''
        Link a keypress to an action.

        Parameters
        ----------
        key : `.Qt.Key`
            The key that should be handled, specified as a ``Qt`` constant, e.g.
            `.Qt.Key_X` or `.Qt.Key_5`.
        modifier : `.Qt.Modifer` or ``None``
            The modifier that needs to be pressed at the same time to trigger
            the action. The modifier needs to be given as a ``Qt`` constant,
            e.g. `.Qt.ShiftModifier` or `.Qt.ControlModifier`. Alternatively,
            ``None`` can be used to specify that the keypress should lead to
            the action independent of the modifier.
        command : method
            A method implementing the action that has been annotated with the
            `@command <.command>` or `@blocking_command <.blocking_command>`
            decorator.
        argument : object, optional
            An additional argument that should be handled to the method defined
            as ``command``. Can be used to re-use the same action in a
            parametrized way (e.g. steps of different size).
        default_doc : bool, optional
            Whether to include the action in the automatically generated help.
            Defaults to ``True``.
        '''
        self.key_actions[(key, modifier)] = (command, argument)
        if default_doc:
            self.help_window.register_key_action(key, modifier,
                                                 command.category,
                                                 command.auto_description(argument))

    def start_task(self, task_name, interface):
        print('start task for interface', interface)
        self.status_bar.clearMessage()
        self.task_progress_text.setText(task_name + '…')
        self.task_progress.setVisible(True)
        self.task_abort_button.setEnabled(True)
        self.task_abort_button.setVisible(True)
        self.running_task = task_name
        self.running_task_interface = interface

    def abort_task(self):
        self.task_abort_button.setEnabled(False)
        self.running_task_interface.abort_task()

    @QtCore.pyqtSlot(int, object)
    def task_finished(self, exit_reason, controller_or_message):
        print('task finished')
        if self.running_task is None:
            # This might be a success message for a non-blocking command
            if isinstance(controller_or_message, str):
                self.status_bar.setStyleSheet('QStatusBar{color: black;}')
                self.status_bar.showMessage(controller_or_message, 1000)
            return  # Nothing else to do

        self.task_progress.setVisible(False)
        self.task_abort_button.setVisible(False)
        # 0: correct execution (no need to show a message)
        if exit_reason == 0:
            text = "Task '{}' finished successfully.".format(self.running_task)
            self.status_bar.setStyleSheet('QStatusBar{color: black;}')
            self.status_bar.showMessage(text, 5000)
        # 1: an error occurred (error will be displayed via `error_status`)
        elif exit_reason == 2:
            text = "Task '{}' aborted.".format(self.running_task)
            self.status_bar.setStyleSheet('QStatusBar{color: black;}')
            self.status_bar.showMessage(text, 5000)

        # If the task was aborted or failed, and the "controller" object has a
        # saved state (e.g. the position of the pipette), ask the user whether
        # they want to reset the state
        if (exit_reason != 0 and
                controller_or_message is not None and
                controller_or_message.has_saved_state()):
            reply = QtWidgets.QMessageBox.question(self, "Reset",
                                                   controller_or_message.saved_state_question,
                                                   QtWidgets.QMessageBox.Yes |
                                                   QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                _, reset_signal = self.interface_signals[self.running_task_interface]
                reset_signal.emit(controller_or_message)

        self.running_task = None
        self.running_task_interface = None

    def keyPressEvent(self, event):
        # We remove the keypad modifier, since we do not want to make a
        # difference between key presses as part of the keypad or on the main
        # keyboard (e.g. for the +/- keys). Most importantly, arrow keys always
        # use the keypad modifier on OS X.
        modifiers = event.modifiers() & ~Qt.KeypadModifier

        # Look for an exact match first (key + modifier)
        event_tuple = (event.key(), int(modifiers))
        description = self.key_actions.get(event_tuple, None)
        # If not found, check for keys that ignore the modifier
        if description is None:
            description = self.key_actions.get((event.key(), None), None)

        if description is not None:
            command, argument = description
            if self.running_task and not command.category == 'General':
                print('another task is running')
                # Another task is running, ignore the key press
                # (we allow the "General" category to still allow to see the
                # help, etc.)
                return
            if command.is_blocking:
                print('blocking')
                self.start_task(command.task_description, command.__self__.interface)
            print('emitting command', self.camera_signal)
            self.camera_signal.emit(command, argument)

    @command(category='General',
             description='Toggle display of keyboard/mouse commands')
    def help_keypress(self):
        self.help_button.click()

    def toggle_help(self):
        if self.help_button.isChecked():
            self.help_window.show()
            # We need to keep the focus
            self.setFocus()
        else:
            self.help_window.setVisible(False)

    @command(category='General',
             description='Toggle display of log output')
    def log_keypress(self):
        self.log_button.click()

    def toggle_log(self):
        if self.log_button.isChecked():
            self.log_window.setVisible(True)
            # We need to keep the focus
            self.setFocus()
        else:
            self.log_window.setVisible(False)

    def set_status_message(self, category, message):
        if message is None and category in self.status_messages:
            del self.status_messages[category]
        else:
            self.status_messages[category] = message

        messages = ' | '.join(self.status_messages.values())
        self.status_label.setText(messages)

    @QtCore.pyqtSlot(float)
    def update_exposure_message(self, exposure):
        self.set_status_message('Camera', 'Exposure %.1fms' % exposure)

    @QtCore.pyqtSlot(int, int)
    def splitter_size_changed(self, pos, index):
        # If the splitter is moved all the way to the right, get back the focus
        if self.splitter.sizes()[1] == 0:
            self.setFocus()
            self.config_button.setChecked(False)
        else:
            self.config_button.setChecked(True)

    def add_config_gui(self, config):
        config_gui = ConfigGui(config)
        self.config_tab.addTab(config_gui, config.name)

    @command(category='General',
             description='Show/hide the configuration pane')
    def configuration_keypress(self):
        self.config_button.click()

    @command(category='General',
             description='Show/hide the overlay information on the image')
    def toggle_overlay(self):
        self.show_overlay = not self.show_overlay

    def toggle_configuration_display(self):
        current_sizes = self.splitter.sizes()
        if current_sizes[1] == 0:
            min_size = self.config_tab.sizeHint().width()
            new_sizes = [current_sizes[0]-min_size, min_size]
            self.config_button.setChecked(True)
        else:
            new_sizes = [current_sizes[0]+current_sizes[1], 0]
            self.setFocus()
            self.config_button.setChecked(False)
        self.splitter.setSizes(new_sizes)


class ElidedLabel(QtWidgets.QLabel):
    def __init__(self, text, minimum_width=200, *args, **kwds):
        self.minimum_width = minimum_width
        self.text = text
        super(ElidedLabel, self).__init__(*args, **kwds)

    def minimumSizeHint(self):
        return QtCore.QSize(self.minimum_width,
                            super(ElidedLabel, self).minimumSizeHint().height())

    def resizeEvent(self, event):
        metric = QtGui.QFontMetrics(self.font())
        elidedText = metric.elidedText(self.text, QtCore.Qt.ElideRight,
                                       self.width())
        self.setText(elidedText)


class ConfigGui(QtWidgets.QWidget):
    value_changed_signal = QtCore.pyqtSignal('QString', object)

    def __init__(self, config, show_name=False):
        super(ConfigGui, self).__init__()
        self.config = config
        self.config._value_changed = self.value_changed
        self.value_changed_signal.connect(self.display_changed_value)
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        top_row = QtWidgets.QHBoxLayout()
        if show_name:
            self.title = QtWidgets.QLabel(config.name)
            self.title.setStyleSheet('font-weight: bold;')
            top_row.addWidget(self.title)
        else:
            top_row.setAlignment(Qt.AlignRight)
        self.load_button = QtWidgets.QToolButton(clicked=self.load_config)
        self.load_button.setIcon(qta.icon('fa.upload'))
        top_row.addWidget(self.load_button)
        self.save_button = QtWidgets.QToolButton(clicked=self.save_config)
        self.save_button.setIcon(qta.icon('fa.download'))
        top_row.addWidget(self.save_button)
        layout.addLayout(top_row)
        all_params = config.params()
        self.value_widgets = {}
        for category, params in config.categories:
            box = QtWidgets.QGroupBox(category)
            rows = QtWidgets.QVBoxLayout()
            for param_name in params:
                param_obj = all_params[param_name]
                row = QtWidgets.QHBoxLayout()
                label = ElidedLabel(param_obj.doc)
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
                self.value_widgets[param_name] = value_widget
                row.addWidget(label, stretch=1)
                row.addWidget(value_widget)
                if isinstance(param_obj, NumberWithUnit):
                    unit_label = QtWidgets.QLabel(param_obj.unit)
                    row.addWidget(unit_label)
                rows.addLayout(row)
            box.setLayout(rows)
            layout.addWidget(box)
        self.setLayout(layout)

    def value_changed(self, key, value):
        if key not in self.value_widgets:
            return
        magnitude = getattr(self.config.params()[key], 'magnitude', 1)
        # We do not update the GUI directly here (that's done in
        # display_changed_value), because it is possible that this is triggered
        # from code running in a different thread
        self.value_changed_signal.emit(key, value/magnitude)

    @QtCore.pyqtSlot('QString', object)
    def display_changed_value(self, key, value):
        widget = self.value_widgets[key]
        if isinstance(widget, QtWidgets.QCheckBox):
            widget.setChecked(value)
        else:
            widget.setValue(value)

    def set_numerical_value(self, name, value):
        setattr(self.config, name, value)

    def set_numerical_value_with_unit(self, name, magnitude, value):
        setattr(self.config, name, value*magnitude)

    def set_boolean_value(self, name, widget):
        setattr(self.config, name, widget.isChecked())

    def save_config(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save configuration",
                                                            filter='Configuration files (*.yaml)',
                                                            options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if filename:
            try:
                self.config.to_file(filename)
            except Exception as ex:
                error_msg = ('Could not save configuration to ' 
                             'file "{}"').format(filename)
                logging.getLogger(__name__).exception(error_msg)
                QtWidgets.QMessageBox.warning(self, 'Saving failed',
                                              error_msg + '\n' + str(ex),
                                              QtWidgets.QMessageBox.Ok)

    def load_config(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load configuration",
                                                            filter='Configuration files (*.yaml)',
                                                            options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if filename:
            try:
                self.config.from_file(filename)
            except Exception as ex:
                error_msg = ('Could not load configuration from ' 
                             'file "{}"').format(filename)
                logging.getLogger(__name__).exception(error_msg)
                QtWidgets.QMessageBox.warning(self, 'Loading failed',
                                              error_msg + '\n' + str(ex),
                                              QtWidgets.QMessageBox.Ok)
