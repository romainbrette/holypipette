from collections import OrderedDict

from PyQt5 import QtCore

from holypipette.executor import TaskExecutor
from holypipette.log_utils import LoggingObject


class Command(object):
    def __init__(self, name, category, description, controller=None, default_arg=None,
                 task_description=None):
        self.default_arg = default_arg
        self.description = description
        self.category = category
        self.controller = controller
        self.name = name
        self.task_description = task_description

    def auto_description(self, argument=None):
        if argument is None:
            argument = self.default_arg
        return self.description.format(argument)


class TaskController(QtCore.QObject, LoggingObject):
    #: Signals the end of a task with an "error code":
    #: 0: successful execution; 1: error during execution; 2: aborted
    task_finished = QtCore.pyqtSignal(int, object)

    def __init__(self):
        super(TaskController, self).__init__()
        self.executors = set()
        self.commands = OrderedDict()

    def add_command(self, name, category, description, default_arg=None,
                    task_description=None):
        command = Command(name, category, description,
                          controller=self, default_arg=default_arg,
                          task_description=task_description)
        self.commands[name] = command

    def connect(self, main_gui):
        pass

    @QtCore.pyqtSlot('QString', object)
    def command_received(self, command, argument):
        try:
            for e in self.executors:
                e.error_occured = False
                e.abort_requested = False
            if self.commands[command].task_description is None:
                self.handle_command(command, argument)
            else:
                self.handle_blocking_command(command, argument)
        except Exception:
            self.exception("An error occured dealing with command "
                           "{}".format(command))
            self.task_finished.emit(1, None)

    def execute(self, executor, func_name, final_task=True, *args, **kwds):
        '''
        Returns True for successful execution (can be used to launch a sequence
        of tasks.
        '''
        executor.save_state()
        executor.execute(func_name, *args, **kwds)
        # We send a reference to the "executor" with the task_finished signal,
        # this can be used to ask the user for a state reset after a failed
        # command (e.g. move back the pipette to its start position in case a
        # calibration failed or was aborted)
        if executor.error_occurred:
            self.task_finished.emit(1, executor)
            return False
        elif executor.abort_requested:
            self.task_finished.emit(2, executor)
            return False
        else:
            executor.delete_state()
            if final_task:
                self.task_finished.emit(0, executor)
            return True

    @QtCore.pyqtSlot(TaskExecutor)
    def reset_requested(self, executor):
        try:
            for e in self.executors:
                e.abort_requested = False
            executor.recover_state()
        except Exception:
            self.exception('Recovering the state for {} failed.'.format(executor))

    def abort_task(self):
        for e in self.executors:
            e.abort_requested = True

    def handle_blocking_command(self, command, argument):
        raise NotImplementedError()

    def handle_command(self, command, argument):
        raise NotImplementedError()
