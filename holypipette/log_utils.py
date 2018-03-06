import logging


class LoggingObject(object):
    @property
    def logger(self):
        if getattr(self, '._logger', None) is None:
            self._logger = logging.getLogger(self.__class__.__module__)
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


def console_logger():
    root_logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s [%(name)s - thread %(thread)d]')
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)