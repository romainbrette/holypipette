import logging


class LoggingObject(object):
    def __init__(self):
        self.logger = None

    def _ensure_logger(self):
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.DEBUG)
        # TODO: Move this part into some global logger object configuration?
        root_logger = logging.getLogger()
        if not len(root_logger.handlers):
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            # TODO: Format log messages
            root_logger.addHandler(handler)

    def debug(self, message, *args, **kwds):
        self._ensure_logger()
        self.logger.debug(message, *args, **kwds)

    def info(self, message, *args, **kwds):
        self._ensure_logger()
        self.logger.info(message, *args, **kwds)

    def warn(self, message, *args, **kwds):
        self._ensure_logger()
        self.logger.warn(message, *args, **kwds)

    def error(self, message, *args, **kwds):
        self._ensure_logger()
        self.logger.error(message, *args, **kwds)

    def exception(self, message, *args, **kwds):
        self._ensure_logger()
        self.logger.exception(message, *args, **kwds)


class TaskExecutor(LoggingObject):
    def __init__(self):
        self.logger = None
        self.error = False
        self.abort_requested = False
        self.saved_state = None

    def run(self, func_name, *args, **kwds):
        func = getattr(self, func_name, None)
        if func is None:
            self.error('Object of type {} does not have a '
                       'function {}.'.format(self.__class__.__name__,
                                             func_name))
            self.error = True
            return

        try:
            self.error = False
            self.abort_requested = False
            func(*args, **kwds)
        except Exception:
            self.exception('An exception occured executing '
                           '{}'.format(func_name))
            self.error = True

    def save_state(self):
        pass

    def reset_state(self):
        pass