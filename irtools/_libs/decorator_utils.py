#! /usr/bin/env python

# Standard Imports
from threading import Thread
from functools import wraps
import collections
import functools

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.decorator')


class Memoized(object):
    """
    Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    SOURCE: https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
    KWARGS SUPPORT: http://stackoverflow.com/a/6408175/1561176
    AND: http://stackoverflow.com/a/20454655/1561176
    """

    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args, **kwargs):
        key = (args, frozenset(sorted(kwargs.items())))
        if not isinstance(key, collections.Hashable):
            # uncacheable. a list, for instance.
            # better to not cache than blow up.
            return self.func(*args, **kwargs)
        if key in self.cache:
            return self.cache[key]
        else:
            value = self.func(*args, **kwargs)
            self.cache[key] = value
            return value

    def __repr__(self):
        """Return the function's docstring."""
        return self.func.__doc__

    def __get__(self, obj, objtype):
        """Support instance methods."""
        p = functools.partial(self.__call__, obj)
        p.repr = repr(self.func)
        return p


def run_async(func):
    """
    Function decorator, intended to make "func" run in a separate thread (asynchronously)
    :param func:
    """
    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target=func, args=args, kwargs=kwargs)
        func_hl.start()
        return func_hl

    return async_func


def run_async_daemon(func):
    """
    Function decorator, intended to make "func" run in a separate thread (asynchronously) as a daemon
    :param func:
    """
    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target=func, args=args, kwargs=kwargs)
        func_hl.daemon = True
        func_hl.start()
        return func_hl

    return async_func


__all__ = ['Memoized', 'run_async', 'run_async_daemon']
