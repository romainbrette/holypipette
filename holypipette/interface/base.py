"""
Package defining the `TaskInterface` class, central to the interface between
GUI and `.TaskController` objects.
"""
import functools
import textwrap
import collections
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

        if wrapped.__doc__ is None:
            import inspect
            try:
                args = inspect.getfullargspec(func).args  # Python 3
            except AttributeError:
                args = inspect.getargspec(func).args  # Python 2
            if len(args) > 1:
                arg_name = args[1]
            else:
                arg_name = None
            docstring = textwrap.dedent('''
            {description}
            ''').format(description=auto_description())

            if arg_name is not None:
                if default_arg is None:
                    default_argument_description = ''
                else:
                    default_argument_description = (
                        ' If no argument is given, {} '
                        'will be used as a default '
                        'argument').format(
                        repr(default_arg))
                docstring += textwrap.dedent('''
                Parameters
                ----------
                {arg_name} : object, optional
                    {default_argument}
                ''').format(arg_name=arg_name,
                            default_argument=default_argument_description)
            wrapped.__doc__ = docstring

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
                result = func(self)
            else:
                result = func(self, argument)
            return result
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

        if wrapped.__doc__ is None:
            import inspect
            try:
                args = inspect.getfullargspec(func).args  # Python 3
            except AttributeError:
                args = inspect.getargspec(func).args  # Python 2
            if len(args) > 1:
                arg_name = args[1]
            else:
                arg_name = None
            docstring = textwrap.dedent('''
            {description}
            ''').format(description=auto_description())

            if arg_name is not None:
                if default_arg is None:
                    default_argument_description = ''
                else:
                    default_argument_description = (
                        ' If no argument is given, {} '
                        'will be used as a default '
                        'argument').format(
                        repr(default_arg))
                docstring += textwrap.dedent('''
                Parameters
                ----------
                {arg_name} : object, optional
                    {default_argument}
                ''').format(arg_name=arg_name,
                            default_argument=default_argument_description)
            wrapped.__doc__ = docstring

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

    def _execute_single_task(self, controller, func, argument):
        controller.save_state()

        self._current_controller = controller
        controller.abort_requested = False
        try:
            if argument is not None:
                func(argument)
            else:
                func()
        # We send a reference to the "controller" with the task_finished signal,
        # this can be used to ask the user for a state reset after a failed
        # command (e.g. move back the pipette to its start position in case a
        # calibration failed or was aborted)
        except RequestedAbortException:
            self.info('Task "{}" aborted'.format(func.__name__))
            self.task_finished.emit(2, controller)
            self._current_controller = None
            return False
        except Exception:
            self.exception('Task "{}" failed'.format(func.__name__))
            self.task_finished.emit(1, controller)
            self._current_controller = None
            return False

        # Task finished successfully
        controller.delete_state()
        self._current_controller = None
        return True

    def execute(self, task, argument=None):
        """
        Execute a function in a `.TaskController` and signal the (successful or
        unsuccessful) completion via the `.task_finished` signal.

        Can either execute a single task or a chain of tasks where each task is
        only executed when the previous was successful.

        Parameters
        ----------
        task: method or list of methods
            A method of a `TaskController` object that should be executed, or
            a list of such methods.
        argument : object or list of object, optional
            An argument that will be provided to ``task`` or ``None`` (the
            default). For a chain of function calls, provide a list of
            arguments.

        Returns
        -------
        success : bool
            Whether the execution was completed successfully. This can be used
            to manually enchain multiple tasks to avoid calling subsequent tasks
            after a failed/aborted task. Note that it can be easier to pass a
            list of functions instead.
        """
        if not isinstance(task, collections.Sequence):
            task = [task]
            argument = [argument]
        if argument is None:
            argument = [None]

        for one_task, one_argument in zip(task, argument):
            controller = one_task.__self__
            if not isinstance(controller, TaskController):
                raise TypeError('Can only execute methods of TaskController'
                                'objects, but object for method {} is of type '
                                '{}'.format(one_task.__name__, type(controller)))
            success = self._execute_single_task(controller, one_task,
                                                one_argument)
            if not success:
                return
        self.task_finished.emit(0, controller)

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
            # Set abort_requested to False, otherwise it will trigger another
            # abort when it uses sleep, etc.
            controller.abort_requested = False
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
