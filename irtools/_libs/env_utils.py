#! /usr/bin/env python

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.env')


def get_ip():
    """Gets the IP of this machine (if it can)"""
    return socket.gethostbyname(socket.gethostname())


def get_env(key, default=None, as_bool=False, as_int=False, clean=True):
    """
    Like os.getenv() but with some more functionality.
    :param key: The os env variable to retrieve
    :param default: The default return value (if is_bool and not default then default is '0')
    :param as_bool: Returns the value as a boolean, also casts the value as an integer first.
    :param as_int: Returns the value as an integer.
    :param clean:  Calls string.strip() on the returned value.
    :return: The Value of the env variable (or default), usually a string, unless as_bool is True.
    """
    # prepare defaults
    if as_bool:
        assert default in (None, True, False)
        default = False if default is None else default
    if as_int:
        assert isinstance(default, (int, type(None)))
        default = 0 if default is None else default
    # get value
    value = os.getenv(key, None)
    # clean
    if clean and value is not None and isinstance(value, str):
        value = value.strip()
    # convert
    if value is None:
        value = default
    elif as_bool:
        if not isinstance(value, bool):
            assert len(value) == 1 and value.isdigit()
            value = bool(int(value))
    elif as_int:
        assert value.isdigit()
        value = int(value)
    elif not isinstance(value, str):
        raise EnvironmentError('key value type invalid: key={} type={} value={}'.format(key, type(value), value))
    return value


__all__ = ['get_env', 'get_ip']
