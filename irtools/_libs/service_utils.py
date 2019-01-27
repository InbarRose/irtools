#! /usr/bin/env python

# Standard Imports
import re
import time
from functools import partial

# Lib Imports
from exec_utils import iexec
from wait_utils import wait_for_callback_value

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.service')

# ignored errors for services
IGNORED_SERVICE_ERRORS = [
    'The service name is invalid',
    'service is not started',
    'The requested service has already been started'
]

# regex for services
SERVICE_QUERY_KEY_VALUE_PATTERN = r'(\S+)\s+:\s+(.+)'
SERVICE_QUERY_KEY_VALUE_RE = re.compile(SERVICE_QUERY_KEY_VALUE_PATTERN)
SERVICE_STATE_PATTERN = r'([A-Z_]+)'
SERVICE_STATE_RE = re.compile(SERVICE_STATE_PATTERN)


def toggle_service_list(service_list, action, **kwargs):
    """
    Toggle service list
    :param service_list: list of service names
    :param action: start, stop, restart
    :param kwargs: kwargs
    :return: 0 if success; otherwise return >0
    """
    stop_on_error = kwargs.pop('stop_on_error', False)
    log.info('toggling service list: service_list={} action={}'.format(service_list, action))
    for service in service_list:
        dump_file = '{}/{}_{}.txt'.format(ir_artifact_dir, action, service)
        log.debug('toggling sql server: service={} action={}'.format(service, action))
        ret = toggle_service(service, action, dump_file=dump_file, **kwargs)
        if ret.contains(IGNORED_SERVICE_ERRORS, any):
            log.trace('Ignoring non-existing service: name={}'.format(service))
            continue
        if ret.bad_rc:
            log.error('Error while stopping the service: name={} rc={} dump_file={}'.format(service, ret.rc, dump_file))
            if stop_on_error:
                return 2
    return 0


def toggle_service(name, action, **kwargs):
    """
    Toggle a service
    :param name: service name
    :param action: start or stop or restart
    :param kwargs: any kwargs to pass to iexec
    :return: ExecResult object
    """
    assert action in ['stop', 'start', 'restart'], 'Unknown action: {}'.format(action)
    kwargs.setdefault('to_console', False)
    kwargs.setdefault('trace_file', ir_log_dir + '/toggle_service.trace.txt')
    if running_on_windows:
        if action == 'restart':
            cmd = 'net stop {n} & net start {n}'.format(n=name)
        else:
            cmd = 'net {} {}'.format(action, name)
    else:
        cmd = 'service {} {}'.format(name, action)
    return iexec(cmd, **kwargs)


def wait_for_service_state(name, state='RUNNING', timeout=30, **kwargs):
    """
    wait for a service to get to a certain state
    :param name:
    :param state:
    :param timeout:
    :param kwargs:
    :return:
    """
    raise_on_timeout = kwargs.pop('raise_on_timeout', True)
    callback = partial(get_service_state, name, **kwargs)
    return wait_for_callback_value(
        callback, state, timeout=timeout, raise_on_timeout=raise_on_timeout, identification='wait_for_service')


def get_service_state(name, **kwargs):
    """
    get the current state of a service
    :param name:
    :param kwargs:
    :return:
    """
    raise_on_fail = kwargs.get('raise_on_fail', False)
    suppress_errors = kwargs.get('suppress_errors', False)
    if running_on_windows:
        try:
            service_dict = query_windows_service(name, **kwargs)
        except Exception as exc:
            log.error('Exception getting service state: service={} exc={}'.format(name, exc))
            if raise_on_fail:
                raise
            return None
        else:
            state = service_dict.get('STATE')
            if state is not None:
                return SERVICE_STATE_RE.search(state).group(1)
            if not suppress_errors:
                log.error('STATE not found: service={} service_dict={}'.format(name, service_dict))
            raise RuntimeError('Could not find STATE for service')

    else:
        log.warn('get_service_state unsupported for linux')
        return None


def query_windows_service(name, **kwargs):
    """query a service on windows"""
    kwargs.setdefault('to_console', False)
    ret = iexec('sc query {}'.format(name), **kwargs)
    return dict(mo.groups() for mo in [SERVICE_QUERY_KEY_VALUE_RE.search(line.strip()) for line in ret.out] if mo)


__all__ = [
    'toggle_service', 'toggle_service_list',
    'wait_for_service_state', 'get_service_state',
    'query_windows_service'
]
