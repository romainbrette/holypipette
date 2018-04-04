"""
Package defining the `Command` and `TaskController` classes, central to the
interface between GUI and `TaskExecutor` objects.
"""
from collections import OrderedDict

from PyQt5 import QtCore

from holypipette.executor import TaskExecutor
from holypipette.log_utils import LoggingObject


class Command(object):
    """
    Simple container to store a "command" supported by a `TaskInterface`.

    Parameters
    ----------
    name : str
        The name of the command (the internally used name that will be used in
        the interface, e.g. "increase_exposure", not a name that is displayed
        to the user)
    category : str
        The category of the command (e.g. "Camera", "Microscope"). Mostly used
        to group commands in the automatically generated GUI documentation.
    description : str
        A description of the command, displayed to the user as part of the
        automatically generated documentation. If the command takes an argument,
        then this description will be formatted with the argument, i.e. it can
        contain format specifications such as `{:.0f}` which will be replaced
        with the argument.
    interface : `TaskInterface`, optional
        The interface responsible for this command. Should always be defined
        except for commands that do not need to be propagated to a interface,
        e.g. GUI commands that trigger changes to the display (e.g. show the
        help window).
    default_arg : object, optional
        The default argument for parametrized commands (e.g. there is only one
        command to move a micro-manipulator horizontally that can be used to
        move it left or right for various distances depending on the argument)
    task_description : str, optional
        A description that will be displayed to the user for a long-running task
        that blocks all other commands (e.g. calibration). Setting it also marks
        this command as a blocking command.
    """
    def __init__(self, name, category, description, interface=None, default_arg=None,
                 task_description=None):
        self.default_arg = default_arg
        self.description = description
        self.category = category
        self.interface = interface
        self.name = name
        self.task_description = task_description

    @property
    def is_blocking(self):
        return self.task_description is not None

    def auto_description(self, argument=None):
        if argument is None:
            argument = self.default_arg
        return self.description.format(argument)


class TaskInterface(QtCore.QObject, LoggingObject):
    """
    Class defining the basic interface between the GUI and the objects
    controlling the hardware. Classes inheritting from this class should:
    * Call this class's ``__init__`` function in its ``__init__` and then add
      all supported commands by calling `add_command`.
    * Overwrite `handle_command` to deal with all declared non-blocking commands
    * Overwrite `handle_blocking_command` to deal with all declared blocking
      commands. To correctly interact with the GUI (show that task is running,
      show error message if task fails, etc.), the method needs to call the
      `execute` function to execute the command.
    """
    #: Signals the end of a task with an "error code":
    #: 0: successful execution; 1: error during execution; 2: aborted
    task_finished = QtCore.pyqtSignal(int, object)

    def __init__(self):
        super(TaskInterface, self).__init__()
        self.executors = set()
        self.commands = OrderedDict()

    def add_command(self, name, category, description, default_arg=None,
                    task_description=None):
        """
        Declare a command that is supported by this `TaskInterface`.

        Parameters
        ----------
        name : str
            The name of the command (the internally used name that will be used in
            the interface, e.g. "increase_exposure", not a name that is displayed
            to the user)
        category : str
            The category of the command (e.g. "Camera", "Microscope"). Mostly used
            to group commands in the automatically generated GUI documentation.
        description : str
            A description of the command, displayed to the user as part of the
            automatically generated documentation. If the command takes an argument,
            then this description will be formatted with the argument, i.e. it can
            contain format specifications such as `{:.0f}` which will be replaced
            with the argument.
        interface : `TaskInterface`, optional
            The interface responsible for this command. Should always be defined
            except for commands that do not need to be propagated to a interface,
            e.g. GUI commands that trigger changes to the display (e.g. show the
            help window).
        default_arg : object, optional
            The default argument for parametrized commands (e.g. there is only one
            command to move a micro-manipulator horizontally that can be used to
            move it left or right for various distances depending on the argument)
        task_description : str, optional
            A description that will be displayed to the user for a long-running task
            that blocks all other commands (e.g. calibration). Setting it also marks
            this command as a blocking command.

        """
        if name in self.commands:
            raise KeyError("A command with the name '{}' has already been "
                           "added ('{}')".format(name,
                                                 self.commands[name].description))
        command = Command(name, category, description,
                          interface=self, default_arg=default_arg,
                          task_description=task_description)
        self.commands[name] = command

    @QtCore.pyqtSlot('QString', object)
    def command_received(self, command, argument):
        """
        Slot that is triggered when the GUI triggers a command handled by this
        `TaskInterface`. Depending on whether the command is blocking or
        non-blocking, it will call `handle_blocking_command` or
        `handle_command`. If an error occurs in the handling of the command
        (e.g., the command cannot be executed because some hardware is missing),
        an error is logged and the `task_finished` signal is emitted.

        Parameters
        ----------
        command : str
            The name of the requested command.
        argument : object
            The argument of the requested command (possibly ``None``).
        """
        try:
            for e in self.executors:
                e.error_occured = False
                e.abort_requested = False
            if self.commands[command].is_blocking:
                self.handle_blocking_command(command, argument)
            else:
                self.handle_command(command, argument)
        except Exception:
            self.exception("An error occured dealing with command "
                           "{}".format(command, argument))
            self.task_finished.emit(1, None)

    def execute(self, executor, func_name, final_task=True, **kwds):
        """
        Execute a function in a `TaskExecutor` and signal the (successful or
        unsuccessful) completion via the `task_finished` signal.

        Parameters
        ----------
        executor : `TaskExecutor`
            The object responsible for executing the task.
        func_name : str
            The name of the function in the ``executor`` object
        final_task : bool, optional
            Whether this call is the final (or only) task that is executed for
            the command. For commands that need to call functions in several
            `TaskExecutor` objects, this will avoid that a successful completion
            triggers the `task_finished` signal (note that error/aborts always
            trigger `task_finished`). Defaults to ``True``
        kwds : dict
            All other keyword arguments will be passed on to
            `TaskExecutor.execute`, which will pass it on to the actual
            function.

        Returns
        -------
        success : bool
            Whether the execution was completed successfully. This is important
            for enchaining multiple tasks (where all but the last are executed
            with ``final_task=False``) to avoid calling subsequent tasks after
            a failed/aborted task.
        """
        executor.save_state()
        executor.execute(func_name, **kwds)
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
        """
        Slot that will be triggered when the user asks for resetting the state
        after an aborted or failed command.

        Parameters
        ----------
        executor : `TaskExecutor`
            The object that was executing the task that failed or was aborted.
            This object is requested to reset its state.

        """
        try:
            for e in self.executors:
                e.abort_requested = False
            executor.recover_state()
        except Exception:
            self.exception('Recovering the state for {} failed.'.format(executor))

    def abort_task(self):
        """
        The user asked for an abort of the currently running (blocking) command.
        We transmit this information to all executing objects (for simplicity,
        only one should be running) by setting the
        `TaskExecutor.abort_requested` attribute. The object runs in a separate
        thread, but will finish its operation as soon as it checks for this
        attribute (either by explicitly checking with
        `TaskExecutor.abort_if_requested`, or by using `TaskExecutor.sleep` or
        one of the logging methods).
        """
        for e in self.executors:
            e.abort_requested = True

    # The following functions have to be implemented if the class declares any
    # blocking/non-blocking commands
    def handle_blocking_command(self, command, argument):
        """
        Handle a blocking command. Should execute all function calls via
        `execute`.

        Parameters
        ----------
        command : str
            The name of the command.
        argument : object
            The argument provided with the command (may be ``None``).
        """
        raise NotImplementedError()

    def handle_command(self, command, argument):
        """Handle a non-blocking command.

        Parameters
        ----------
        command : str
            The name of the command.
        argument : object
            The argument provided with the command (may be ``None``)."""

    # This function will be automatically called by the main GUI and can be
    # overwritten to connect signals in this class to the main GUI (e.g. to
    # update information in the status bar)
    def connect(self, main_gui):
        """
        Connect signals to slots in the main GUI. Will be called automatically
        during initialization of the GUI.

        Parameters
        ----------
        main_gui : `CameraGui`
            The main GUI in control.
        """
        pass
