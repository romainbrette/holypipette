"""
Package defining the `TaskInterface` class, central to the interface between
GUI and `.TaskController` objects.
"""
import functools
from types import MethodType

from PyQt5 import QtCore

from holypipette.controller import TaskController, RequestedAbortException
from holypipette.log_utils import LoggingObject


def command(category, description, default_arg=None, success_message=None):
    '''
    Decorator that annotates a function with information about the implemented
    command.

    Parameters
    ----------
    category : str
        The command category (used for structuring the help window).
    description : str
        A descriptive text for the command (used in the help window).
    default_arg : object, optional
        A default argument provided to the method or ``None`` (the default).
    success_message : str, optional
        A message that will be displayed in the status bar of the GUI window
        after the execution of the command. For simple commands that have visual
        feedback, e.g. moving the manipulator or changing the exposure time,
        this should not be set to avoid unnecessary messages. For actions that
        have no visual feedback, e.g. storing a position, this should be set to
        give the user an indication that something happened.
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapped(self, argument=None):
            if argument is None and default_arg is not None:
                argument = default_arg
            if argument is None:
                result = func(self)
                if success_message:
                    self.task_finished.emit(0, success_message)
                    self.info(success_message)
                return result
            else:
                result = func(self, argument)
                if success_message:
                    self.task_finished.emit(0, success_message)
                    self.info(success_message)
                return result
        wrapped.category = category
        wrapped.description = description
        wrapped.default_arg = default_arg
        wrapped.is_blocking = False

        def auto_description(argument=None):
            if argument is None:
                argument = default_arg
            return description.format(argument)
        wrapped.auto_description = auto_description

        return wrapped
    return decorator


def blocking_command(category, description, task_description,
                     default_arg=None):
    '''
    Decorator that annotates a function with information about the implemented
    (blocking) command.

    Parameters
    ----------
    category : str
        The command category (used for structuring the help window).
    description : str
        A descriptive text for the command (used in the help window).
    task_description : str
        Text that will be displayed to the user while the task is running
    default_arg : object, optional
        A default argument provided to the method or ``None`` (the default).
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapped(self, argument=None):
            if argument is None and default_arg is not None:
                argument = default_arg
            if argument is None:
                return func(self)
            else:
                return func(self, argument)
        wrapped.category = category
        wrapped.description = description
        wrapped.task_description = task_description
        wrapped.is_blocking = True
        wrapped.default_arg = default_arg

        def auto_description(argument=None):
            if argument is None:
                argument = default_arg
            return description.format(argument)
        wrapped.auto_description = auto_description

        return wrapped
    return decorator


class TaskInterface(QtCore.QObject, LoggingObject):
    """
    Class defining the basic interface between the GUI and the objects
    controlling the hardware. Classes inheriting from this class should:

    * Call this class's ``__init__`` function in its ``__init__``
    * Annotate all functions providing commands with the `@command <.command>`
      or `@blocking_command <.blocking_command>` decorator.
    * To correctly interact with the GUI for blocking commands (show that task
      is running, show error message if task fails, etc.), the method needs to
      call the `~.TaskInterface.execute` function to execute the command.
    """
    #: Signals the end of a task with an "error code":
    #: 0: successful execution; 1: error during execution; 2: aborted
    task_finished = QtCore.pyqtSignal(int, object)

    def __init__(self):
        super(TaskInterface, self).__init__()
        self._current_controller = None

    @QtCore.pyqtSlot(MethodType, object)
    def command_received(self, command, argument):
        """
        Slot that is triggered when the GUI triggers a command handled by this
        `.TaskInterface`. If an error occurs in the handling of the command
        (e.g., the command does not exist or received the wrong number of
        arguments), an error is logged and the `.task_finished` signal is
        emitted. Note that the handling of errors *within* the command, as well
        as the handling of abort requests is performed in the `.execute` method.

        Parameters
        ----------
        command : method
            A reference to the requested command.
        argument : object
            The argument of the requested command (possibly ``None``).
        """
        try:
            if argument is None:
                command()
            else:
                command(argument)
        except Exception:
            self.exception('"{}" failed.'.format(command.__name__))
            self.task_finished.emit(1, None)

    def execute(self, controller, func_name, argument=None, final_task=True):
        """
        Execute a function in a `.TaskController` and signal the (successful or
        unsuccessful) completion via the `.task_finished` signal.

        Parameters
        ----------
        controller : `.TaskController`
            The object responsible for executing the task.
        func_name : str
            The name of the function in the ``controller`` object
        argument : object, optional
            An argument that will be provided to ``func_name`` or ``None`` (the
            default).
        final_task : bool, optional
            Whether this call is the final (or only) task that is executed for
            the command. For commands that need to call functions in several
            `.TaskController` objects, this will avoid that a successful
            completion triggers the `.task_finished` signal (note that
            error/aborts always trigger `.task_finished`). Defaults to ``True``

        Returns
        -------
        success : bool
            Whether the execution was completed successfully. This is important
            for enchaining multiple tasks (where all but the last are executed
            with ``final_task=False``) to avoid calling subsequent tasks after
            a failed/aborted task.
        """
        controller.save_state()
        func = getattr(controller, func_name, None)
        if func is None:
            raise AttributeError('Object of type {} does not have a '
                                 'function {}.'.format(self.__class__.__name__,
                                                       func_name))

        # We send a reference to the "controller" with the task_finished signal,
        # this can be used to ask the user for a state reset after a failed
        # command (e.g. move back the pipette to its start position in case a
        # calibration failed or was aborted)
        self._current_controller = controller
        controller.abort_requested = False
        try:
            if argument is not None:
                func(argument)
            else:
                func()
        except RequestedAbortException:
            self.info('Task "{}" aborted'.format(func_name))
            self.task_finished.emit(2, controller)
            self._current_controller = None
            return False
        except Exception:
            self.exception('Task "{}" failed'.format(func_name))
            self.task_finished.emit(1, controller)
            self._current_controller = None
            return False

        # Task finished successfully
        controller.delete_state()
        # TODO: Move this into the blocking command decorator
        if final_task:
            self.task_finished.emit(0, controller)
        self._current_controller = None
        return True

    @QtCore.pyqtSlot(TaskController)
    def reset_requested(self, controller):
        """
        Slot that will be triggered when the user asks for resetting the state
        after an aborted or failed command.

        Parameters
        ----------
        controller : `.TaskController`
            The object that was executing the task that failed or was aborted.
            This object is requested to reset its state.

        """
        try:
            controller.recover_state()
        except Exception:
            self.exception('Recovering the state for {} failed.'.format(controller))

    def abort_task(self):
        """
        The user asked for an abort of the currently running (blocking) command.
        We transmit this information to all executing objects (for simplicity,
        only one should be running) by setting the
        `TaskController.abort_requested` attribute. The object runs in a separate
        thread, but will finish its operation as soon as it checks for this
        attribute (either by explicitly checking with
        `.TaskController.abort_if_requested`, or by using
        `.TaskController.sleep` or one of the logging methods).
        """
        self._current_controller.abort_requested = True

    # This function will be automatically called by the main GUI and can be
    # overwritten to connect signals in this class to the main GUI (e.g. to
    # update information in the status bar)
    def connect(self, main_gui):
        """
        Connect signals to slots in the main GUI. Will be called automatically
        during initialization of the GUI.

        Parameters
        ----------
        main_gui : `.CameraGui`
            The main GUI in control.
        """
        pass
