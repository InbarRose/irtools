#! /usr/bin/env python

# Standard Imports

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.func')


def get_func_name(func, raise_on_fail=True, raise_on_lambda=False):
    func_name = None
    if callable(func):
        try:
            func_name = getattr(func, 'func_name', None)
        except AttributeError:
            func_name = getattr(func, '__name__', None)
    elif raise_on_fail:
        raise RuntimeError('func is not a function: func={} type={}'.format(func, type(func)))

    if func_name is None and raise_on_fail:
        raise RuntimeError('could not get func_name from func: func={}'.format(func))

    if raise_on_lambda and func_name == '<lambda>':
        raise RuntimeError('could not get func_name from lambda (they have none): lambda={}'.format(func))

    return func_name


__all__ = ['get_func_name']
