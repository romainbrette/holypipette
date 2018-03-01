from collections import OrderedDict

from PyQt5 import QtCore

from base.executor import LoggingObject


class Command(object):
    def __init__(self, name, category, description, controller=None, default_arg=None):
        self.default_arg = default_arg
        self.description = description
        self.category = category
        self.controller = controller
        self.name = name

    def auto_description(self, argument=None):
        if argument is None:
            argument = self.default_arg
        return self.description.format(argument)


class TaskController(QtCore.QObject, LoggingObject):
    #: Signals the end of a task with an "error code":
    #: 0: successful execution; 1: error during execution; 2: aborted
    task_finished = QtCore.pyqtSignal(int)

    def __init__(self):
        super(TaskController, self).__init__()
        self.executors = set()
        self.commands = OrderedDict()

    def add_command(self, name, category, description, default_arg=None):
        command = Command(name, category, description,
                          controller=self, default_arg=default_arg)
        self.commands[name] = command

    def connect(self, main_gui):
        pass

    @QtCore.pyqtSlot('QString', object)
    def command_received(self, command, argument):
        try:
            self.handle_command(command, argument)
        except Exception:
            self.exception("An error occured dealing with command "
                           "{}".format(command))
            self.task_finished.emit(1)

    def handle_command(self, command, argument):
        raise NotImplementedError()

    def abort_task(self):
        for e in self.executors:
            e.abort_requested = True
