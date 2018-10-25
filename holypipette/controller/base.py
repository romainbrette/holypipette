"""
Module defining the `TaskController` class.
"""
import functools
import time

from holypipette.log_utils import LoggingObject


class RequestedAbortException(Exception):
    """Exception that should be raised when a function aborts its execution due
       to ``abort_requested``."""
    pass


def check_for_abort(obj, func):
    """Decorator to make a function raise a `RequestedAbortException` if
       ``abort_requested`` attribute is set."""
    @functools.wraps(func)
    def decorated(*args, **kwds):
        if getattr(obj, 'abort_requested', False):
            raise RequestedAbortException()
        return func(*args, **kwds)
    return decorated


class TaskController(LoggingObject):
    """
    Base class for objects that control the high-level logic to control the
    hardware, e.g. the calibration of a manipulator or the steps to follow for
    a patch clamp experiment. Objects will usually be instantiated from more
    specific subclasses.

    The class provides several convenient ways to interact with an
    asynchronously requested abort of the current task. A long-running task
    can check explicitly whether an abort has been requested with
    `abort_if_requested` which will raise a `RequestedAbortException` if the
    ``abort_requested`` attribute has been set. This check will also be
    performed automatically if `~TaskController.debug`,
    `~TaskController.info`, or
    `~TaskController.warn` is called (which otherwise simply forward their
    message to the logging system). Finally, tasks should call `sleep`
    (instead of `time.sleep`) which will periodically check for an abort
    request during the sleep time.
    """
    def __init__(self):
        super(TaskController, self).__init__()
        self.abort_requested = False
        self.saved_state = None
        self.saved_state_question = None
        # Overwrite the logging functions so that they check for `abort_requested`
        self.debug = check_for_abort(self, self.debug)
        self.info = check_for_abort(self, self.info)
        self.warn = check_for_abort(self, self.warn)

    def abort_if_requested(self):
        """
        Checks for an abort request and interrupts the current task if
        necessary. Can be explicitly called during long-running tasks, but will
        also be called automatically by the logging functions `debug`, `info`,
        `warn`, or the wait function `sleep`.
        Raises
        ------
        RequestedAbortException
            If the `abort_requested` attribute is set
        """
        if self.abort_requested:
            raise RequestedAbortException()

    def sleep(self, seconds):
        """Convenience function that sleeps (as `time.sleep`) but remains
        sensitive to abort requests"""
        check_every = 0.25
        start = time.time()
        self.abort_if_requested()
        while time.time() - start < (seconds-check_every):
            time.sleep(check_every)
            self.abort_if_requested()

        remaining = seconds - (time.time() - start)
        if remaining > 0:
            time.sleep(remaining)
        self.abort_if_requested()

    # SAVED STATES:
    # Functions to overwrite to enable a reset of the state after a failed or
    # aborted task. Note that these functions are used for resets that are
    # optional, i.e. will only be performed after asking the user (with the
    # question defined in the `saved_state_question` attribute). For important
    # resets that should be performed right-away, regardless of any
    # user-interaction (e.g. resetting the pressure of the pressure controller),
    # rather use a try/finally construct in the respective function
    def save_state(self):
        """
        Save the current state (e.g. the position of the manipulators) for
        later recovery in the case of a failure or abort. Has to be overwritten
        in subclasses. Should save the state to the `saved_state` variable or
        overwrite `has_saved_state` as well.
        """
        pass

    def has_saved_state(self):
        """
        Whether this object has a saved state that can be recovered with
        `recover_state`.

        Returns
        -------
        has_state : bool
            Whether this object has a saved state. By default, checks whether
            the `saved_state` attribute is not ``None``.
        """
        return self.saved_state is not None

    def delete_state(self):
        """
        Delete any previously saved state. By default, overwrites the
        `saved_state` attribute with ``None``.
        """
        self.saved_state = None

    def recover_state(self):
        """
        Recover the state (e.g. the position of the manipulators) after a
        failure or abort. Has to be overwritten in subclasses.
        """
        pass
