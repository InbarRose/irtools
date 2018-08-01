#! /usr/bin/env python

# Lib Imports
from file_utils import check_makedir

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.log')

# constant that will be changed with global call
logging_is_setup = False

# logging helpers
LOG_LEVEL_MAP_FUNC = {
    0: log.info,
    1: log.debug,
    2: log.trace,
}
LOG_LEVEL_MAP_NAME = {
    0: 'INFO',
    1: 'DEBUG',
    2: 'TRACE',
}

# we don't want the hostname field to stretch if its too long, so lets truncate after 16 chars.
if len(current_hostname) > 16:
    host_log_name = current_hostname[:15] + '~'
else:
    host_log_name = current_hostname
# lets create a nice log format to use
# the logging date time format
log_datetime_format = '%Y-%m-%d %H:%M:%S'
LOG_FORMAT = logging.Formatter(
    '%(asctime)s {host} %(name)s %(levelname)5.5s: %(message)s'.format(host=host_log_name),
    datefmt=log_datetime_format)
# special log format for extreme trace (includes filename and line number)
LOG_FORMAT_EXTRA = logging.Formatter(
    '%(asctime)s {host} [%(name)s %(filename)s:%(lineno)s] %(levelname)5.5s: %(message)s'.format(
        host=host_log_name),
    datefmt=log_datetime_format)


def test_logging():
    log.info('log info message')
    log.debug('log debug message: param=value')
    log.warn('log warning!')
    log.error('log error message')
    log.trace('trace log!')


def get_log_func(level):
    """
    Returns a logger for the given level
    :param level: int {0: info, 1: debug, 2: trace}
    :return: log.LEVEL function
    """
    return LOG_LEVEL_MAP_FUNC[int(level)]


def get_log_level_name(log_level):
    """
    Returns the log level string for the given level
    :param log_level: int {0: info, 1: debug, 2: trace}
    :return: log level string
    """
    return LOG_LEVEL_MAP_NAME[int(log_level)]


def add_file_log_handler(log_, path, level=logging.TRACE, **kwargs):
    """
    add a logging file handler to a log
    :param log_:
    :param path:
    :param level:
    :param kwargs:
    :return:
    """
    try:
        check_makedir(os.path.dirname(path))
        fh = logging.FileHandler(path)
        fh.setLevel(level)
        fh.setFormatter(kwargs.get('format', LOG_FORMAT))
        log_.addHandler(fh)
    except Exception as exc:
        log.error('Exception adding log handler to log: log={} exc={}'.format(log_.name, exc))
        return False
    else:
        return True


def add_console_log_handler(log_, level=logging.TRACE, **kwargs):
    """
    add a logging file handler to a log
    :param log_:
    :param level:
    :param kwargs:
    :return:
    """
    try:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(kwargs.get('format', LOG_FORMAT))
        log_.addHandler(ch)
    except Exception as exc:
        log.error('Exception adding console handler to log: log={} exc={}'.format(log_.name, exc))
        return False
    else:
        return True


def set_log_console_handler_to_level(log_, level=logging.WARN, **kwargs):
    """
    set the console handler of a log to specified level
    :param log_: the log to change the console handler of
    :param level: the level to set the console handler to
    :param kwargs:
    :return:
    """
    # noinspection PyProtectedMember
    assert level in logging._levelNames
    # noinspection PyProtectedMember
    level_name = logging._levelNames.get(level)
    console_handlers = filter(lambda h: isinstance(h, logging.StreamHandler), log_.handlers)
    if not console_handlers:
        log.warn('can not set log console handler, none found: log={}'.format(log_.name, level_name))
        return
    for console_handler in console_handlers:
        if console_handler.level == level:
            continue
        log.debug('setting log console handler to level: log={} handler={} level={}'.format(
            log_.name, console_handler, level_name))
        console_handler.setLevel(level)
        if console_handler.level != level:
            log.error('failed to set console handler to level: handler={} level={}'.format(console_handler, level_name))


def logging_setup(**kwargs):
    """
    Sets up logging on the machine, using the following hierarchy of kwargs for determining level:
    trace, debug, log_level, level
    with optional log_file param
    :param trace: enables trace level
    :param debug: enables debug level
    :param log_level: logging level to use for stream handler (0=info, 1=debug, 2=trace)
    :param level: logging level to use for stream handler (logging.INFO, logging.DEBUG, etc)
    :param log_file: (optional) write a log file to this location
    :return: None
    """
    global logging_is_setup
    if logging_is_setup:
        log.trace('Requested logging_setup, but logging is already setup, ignoring.')
        return

    log_format_console = LOG_FORMAT
    log_format_file = LOG_FORMAT
    # == read params for console ==
    if kwargs.get('extra') or kwargs.get('log_level') in ['3', 3]:
        level = logging.TRACE
        log_format_console = LOG_FORMAT_EXTRA
    elif kwargs.get('trace') or kwargs.get('log_level') in ['2', 2]:
        level = logging.TRACE
    elif kwargs.get('debug') or kwargs.get('log_level') in ['1', 1]:
        level = logging.DEBUG
    else:
        level = kwargs.get('level', logging.INFO)

    # == read params for file ==
    log_file = kwargs.get('log_file')
    if kwargs.get('log_file_level') in ['3', 3]:
        log_file_level = logging.TRACE
        log_format_file = LOG_FORMAT_EXTRA
    elif kwargs.get('log_file_level') in ['2', 2, None]:  # default
        log_file_level = logging.TRACE
    elif kwargs.get('log_file_level') in ['1', 1]:
        log_file_level = logging.DEBUG
    else:
        log_file_level = logging.INFO

    # init logger
    root = logging.getLogger()
    root.setLevel(logging.TRACE)

    # console logging
    # note: if a log is sending to console because of root logger, we can set propagate=0 for that logger
    add_console_log_handler(root, level, format=log_format_console)

    # file logging
    if log_file:
        add_file_log_handler(root, log_file, log_file_level, format=log_format_file)

    # notify about logging
    if not kwargs.get('no_log'):
        log.info('Logging Setup complete: level={} file={}'.format(logging.getLevelName(level), log_file))
        log.trace('Logging command line: {}'.format(sys.argv))

    # enable warnings in logs
    capture_warnings = kwargs.get('capture_warnings', True)
    if capture_warnings:
        logging.captureWarnings(True)
        log.trace('enabled capture warnings in logs')

    # toggle global
    logging_is_setup = True


__all__ = [
    'logging_setup', 'add_console_log_handler', 'add_file_log_handler',
    'get_log_func', 'get_log_level_name', 'test_logging',
    'set_log_console_handler_to_level', 'log_datetime_format'
]
