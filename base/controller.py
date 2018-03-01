from PyQt5 import QtCore

from base.executor import LoggingObject

class TaskController(QtCore.QObject,LoggingObject):
    #: Signals the end of a task with an "error code":
    #: 0: successful execution; 1: error during execution; 2: aborted
    task_finished = QtCore.pyqtSignal(int)

    def __init__(self):
        super(TaskController, self).__init__()
        self.executors = set()

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
