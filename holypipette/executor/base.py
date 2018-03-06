import functools
import time

from holypipette.log_utils import LoggingObject


class RequestedAbortException(Exception):
    '''Exception that should be raised when a function aborts its exectuion due
       to ``abort_requested``.'''
    pass


def check_for_abort(obj, func):
    '''Decorator to make a function raise a `RequestedAbortException` if
       ``abort_requested`` attribute is set.'''
    @functools.wraps(func)
    def decorated(*args, **kwds):
        if getattr(obj, 'abort_requested', False):
            raise RequestedAbortException()
        return func(*args, **kwds)
    return decorated


class TaskExecutor(LoggingObject):
    def __init__(self):
        super(TaskExecutor, self).__init__()
        self.error_occurred = False
        self.abort_requested = False
        self.saved_state = None
        self.saved_state_question = None
        # Overwrite the logging functions so that they check for `abort_requested`
        self.debug = check_for_abort(self, self.debug)
        self.info = check_for_abort(self, self.info)
        self.warn = check_for_abort(self, self.warn)

    def run(self, func_name, *args, **kwds):
        func = getattr(self, func_name, None)
        if func is None:
            self.error('Object of type {} does not have a '
                       'function {}.'.format(self.__class__.__name__,
                                             func_name))
            self.error_occurred = True
            return

        try:
            self.error_occurred = False
            self.abort_requested = False
            func(*args, **kwds)
        except RequestedAbortException:
            # We don't want the debug command to raise the exception again,
            # so temporarily disable the `abort_requested` attribute
            self.abort_requested = False
            self.debug('command "{}" has been aborted.'.format(func_name))
            # Set the attribute again so that later code knows about the abort
            self.abort_requested = True
        except Exception:
            self.exception('An exception occured executing '
                           '{}'.format(func_name))
            self.error_occurred = True

    def abort_if_requested(self):
        '''This function should be called regularly during long_running tasks'''
        if self.abort_requested:
            raise RequestedAbortException()

    def sleep(self, seconds):
        '''Convenience function that sleeps but remains sensitive to abort
        requests'''
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

    def save_state(self):
        pass

    def delete_state(self):
        pass

    def recover_state(self):
        pass
