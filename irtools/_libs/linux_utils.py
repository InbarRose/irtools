#! /usr/bin/env python

# Lib Imports
from exec_utils import iexec

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.linux')


def rm_rf(*paths, **kwargs):
    """Use rm -rf on the paths"""
    assert running_on_linux
    log.info('Cleaning paths with rm -rf: paths={}'.format(list(paths)))
    # note: perhaps add protection against certain paths? ('/')
    return iexec('rm -rf {}'.format(' '.join(paths)), **kwargs)


def chmod(fpath, mode='0777', **kwargs):
    """use chmod on path"""
    assert running_on_linux
    kwargs.setdefault('to_console', False)
    kwargs.setdefault('log_as_trace', True)
    if os.path.isdir(fpath):
        cmd = 'chmod {m} -R {p}'
    else:
        cmd = 'chmod {m} {p}'
    return iexec(cmd.format(m=mode, p=fpath), **kwargs)


__all__ = ['rm_rf', 'chmod']
