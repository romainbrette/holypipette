import functools
import logging
import time


class RequestedAbortException(Exception):
    '''Exception that should be raised when a function aborts its exectuion due
       to ``abort_requested``.'''
    pass


def console_logger():
    root_logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s [%(name)s - thread %(thread)d]')
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)


class LoggingObject(object):
    @property
    def logger(self):
        if getattr(self, '._logger', None) is None:
            self._logger = logging.getLogger(__name__)
            self._logger.setLevel(logging.DEBUG)
        return self._logger

    def debug(self, message, *args, **kwds):
        self.logger.debug(message, *args, **kwds)

    def info(self, message, *args, **kwds):
        self.logger.info(message, *args, **kwds)

    def warn(self, message, *args, **kwds):
        self.logger.warn(message, *args, **kwds)

    def error(self, message, *args, **kwds):
        self.logger.error(message, *args, **kwds)

    def exception(self, message, *args, **kwds):
        self.logger.exception(message, *args, **kwds)


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

        time.sleep(seconds - (time.time() - start))
        self.abort_if_requested()

    def save_state(self):
        pass

    def reset_state(self):
        pass
