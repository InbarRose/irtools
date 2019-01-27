#! /usr/bin/env python

# Standard Imports
import time
import uuid

# irtools Imports
from irtools import *
from enum_utils import enum

# logging
log = logging.getLogger('irtools.utils.wait')

WaitStatus = enum(ready='READY', wait='WAIT', fail='FAIL', timeout='TIMEOUT', error='ERROR')


class WaitLib(object):
    """wait for something, supports ready, fail, and wait function calls to check status"""

    _default_timeout = 120     # default no timeout (2 minutes)
    _default_period = 1      # default wait 1 second between checks
    _default_grace_time = 0  # default don't wait before starting to check
    _default_ready_values = None  # None - default behaviour (truthy = ready) / else contains result
    _default_fail_values = None   # None - default behaviour (None = wait) / else contains result
    _default_wait_values = None   # None - default behaviour (falsey = fail) / else contains result

    def __init__(self, **kwargs):
        # identification arguments
        self.identification = kwargs.pop('identification', '')
        self._uuid = kwargs.pop('uuid', None) or uuid.uuid4()
        # gather process arguments
        self.timeout = kwargs.pop('timeout', None) or self._default_timeout
        self.period = kwargs.pop('period', None) or self._default_period
        self.grace_time = kwargs.pop('grace_time', None) or self._default_grace_time
        assert isinstance(self.grace_time, int) and self.grace_time >= 0
        assert isinstance(self.period, (int, float)) and self.period > 0
        assert isinstance(self.timeout, int) and self.timeout >= self.grace_time + self.period
        # gather process operating arguments (flags)
        self.log_process = kwargs.pop('log_process', True)
        self.log_trace = kwargs.pop('log_trace', False)
        self.raise_on_timeout = kwargs.pop('raise_on_timeout', True)
        self.stop_on_exception = kwargs.pop('stop_on_exception', True)
        self.raise_on_exception = kwargs.pop('raise_on_exception', True)
        self.return_wait_status = kwargs.pop('return_wait_status', False)
        self.no_fail = kwargs.pop('no_fail', False)  # to disable fail checking (only check ready or keep waiting)
        assert isinstance(self.log_process, bool)
        assert isinstance(self.log_trace, bool)
        assert isinstance(self.raise_on_timeout, bool)
        assert isinstance(self.raise_on_exception, bool)
        assert isinstance(self.return_wait_status, bool)
        assert isinstance(self.no_fail, bool)
        # gather check_methods
        self.check_ready_method = kwargs.pop('ready_method')
        self.check_ready_values = kwargs.pop('ready_values', self._default_ready_values)
        self.check_fail_method = kwargs.pop('fail_method')
        self.check_fail_values = kwargs.pop('fail_values', self._default_fail_values)
        self.check_wait_method = kwargs.pop('wait_method')
        self.check_wait_values = kwargs.pop('wait_values', self._default_wait_values)
        assert callable(self.check_ready_method)
        assert callable(self.check_fail_method)
        assert callable(self.check_wait_method)
        # members
        self.status = WaitStatus.wait
        self.result = None
        self.error = None
        # time members
        self.start_time = None
        self.end_time = None
        self.elapsed_time = None

    @property
    def wait_id(self):
        parts = self._get_wait_id_parts()
        return 'Wait({})'.format(' '.join(parts))

    def _get_wait_id_parts(self):
        parts = []
        if self.identification:
            parts.append('id={}'.format(self.identification))
        if self.timeout:
            parts.append('timeout={}'.format(self.timeout))
        return parts

    def wait(self):
        if self.log_process:
            log.info('wait Starting: {}'.format(self.wait_id))
        self.start_time = time.time()
        self._wait_process()
        self.end_time = time.time()
        if self.log_process:
            log.info('wait Finished: {} status={} elapsed={}'.format(self.wait_id, self.status, self.elapsed_time))
        if self.return_wait_status:
            return self.status
        else:
            return self.is_ready

    def _wait_process(self):
        while self.is_wait:
            # get elapsed time
            self.elapsed_time = time.time() - self.start_time
            # check status
            self.get_status()
            # do period
            self._do_period()

    def _do_period(self):
        if self.is_wait:
            time.sleep(self.period)

    def get_status(self):
        if not self.is_wait:
            # status already set
            return self.status
        # check the status
        self.check_ready()
        if self.is_ready:
            return self.status
        self.check_fail()
        if self.is_fail:
            return self.status
        self.check_wait()
        if self.is_wait:
            return self.status
        self.check_timeout()
        if self.is_timeout:
            return self.status
        # if we get here we have a problem
        self.set_error('could not resolve status')
        return self.status

    def check_ready(self):
        try:
            if self.log_trace:
                log.trace('wait calling check_ready method: {} method={}'.format(self.wait_id, self.check_ready_method))
            r = self.check_ready_method()
        except Exception as exc:
            if self.log_process:
                log.error(
                    'wait exception calling check_ready method: {} method={} exc={} trace...'.format(
                        self.wait_id, self.check_ready_method, exc),
                    exc_info=not bool(self.raise_on_exception))
            if self.stop_on_exception:
                self.set_error('exception calling check_ready')
            if self.raise_on_exception:
                raise
        else:
            if self.log_trace:
                log.trace('wait check_ready method result: {} result={}'.format(self.wait_id, r))
            if (self.check_ready_values is None and bool(r) is True) or \
                    (isinstance(self.check_ready_values, (list, tuple, set)) and r in self.check_ready_values):
                if self.log_process:
                    log.debug('wait Ready: {} r={}'.format(self.wait_id, r))
                self.set_ready(r)

    def check_fail(self):
        if self.no_fail:
            return
        try:
            if self.log_trace:
                log.trace('wait calling check_fail method: {} method={}'.format(self.wait_id, self.check_fail_method))
            r = self.check_fail_method()
        except Exception as exc:
            if self.log_process:
                log.error(
                    'wait exception calling check_fail method: {} method={} exc={} trace...'.format(
                        self.wait_id, self.check_fail_method, exc),
                    exc_info=not bool(self.raise_on_exception))
            if self.stop_on_exception:
                self.set_error('exception calling check_fail')
            if self.raise_on_exception:
                raise
        else:
            if self.log_trace:
                log.trace('wait check_fail method result: {} result={}'.format(self.wait_id, r))
            if (self.check_fail_values is None and bool(r) is False) or \
                    (isinstance(self.check_fail_values, (list, tuple, set)) and r in self.check_fail_values):
                if self.log_process:
                    log.debug('wait Fail: {} r={}'.format(self.wait_id, r))
                self.set_fail(r)

    def check_wait(self):
        # this whole method might be unnecessary (since we should keep waiting until ready/timeout/fail anyway)
        try:
            if self.log_trace:
                log.trace('wait calling check_wait method: {} method={}'.format(self.wait_id, self.check_wait_method))
            r = self.check_wait_method()
        except Exception as exc:
            if self.log_process:
                log.error(
                    'wait exception calling check_wait method: {} method={} exc={} trace...'.format(
                        self.wait_id, self.check_wait_method, exc),
                    exc_info=not bool(self.raise_on_exception))
            if self.stop_on_exception:
                self.set_error('exception calling check_wait')
            if self.raise_on_exception:
                raise
        else:
            if self.log_trace:
                log.trace('wait check_wait method result: {} result={}'.format(self.wait_id, r))
            if (self.check_wait_values is None and r is None) or \
                    (isinstance(self.check_wait_values, (list, tuple, set)) and r in self.check_wait_values):
                if self.log_process:
                    log.debug('wait Waiting: {} r={}'.format(self.wait_id, r))
                self.set_wait(r)

    def check_timeout(self):
        if self.timeout and self.elapsed_time > self.timeout:
            self.set_timeout()
            msg = 'wait Timed out: {} elapsed={}'.format(self.wait_id, self.elapsed_time)
            if self.log_process:
                log.error(msg)
            if self.raise_on_timeout:
                raise RuntimeError(msg)

    def set_ready(self, result):
        self.result = result
        self.status = WaitStatus.ready

    def set_fail(self, result):
        self.result = result
        self.status = WaitStatus.fail

    def set_wait(self, result):
        self.result = result
        self.status = WaitStatus.wait

    def set_timeout(self):
        self.status = WaitStatus.timeout

    def set_error(self, error):
        if self.log_process:
            log.error('wait Error: {} msg={}'.format(self.wait_id, error))
        self.error = error
        self.status = WaitStatus.error

    @property
    def is_ready(self):
        return bool(self.status == WaitStatus.ready)

    @property
    def is_wait(self):
        return bool(self.status == WaitStatus.wait)

    @property
    def is_fail(self):
        return bool(self.status == WaitStatus.fail)

    @property
    def is_timeout(self):
        return bool(self.status == WaitStatus.timeout)

    @property
    def is_error(self):
        return bool(self.status == WaitStatus.error)


class WaitCallback(WaitLib):
    """wait for something using a single callback function"""

    def __init__(self, callback, **kwargs):
        assert callable(callback)
        if hasattr(callback, 'func_name'):
            kwargs.setdefault('identification', callback.func_name)
        self.latest_callback_result = None
        self.return_callback_result = kwargs.pop('return_callback_result', False)
        kwargs.setdefault('ready_method', callback)
        kwargs.setdefault('fail_method', callback)
        kwargs.setdefault('wait_method', callback)
        super(WaitCallback, self).__init__(**kwargs)

    def set_ready(self, result):
        super(WaitCallback, self).set_ready(result)
        self.latest_callback_result = result

    def set_fail(self, result):
        super(WaitCallback, self).set_fail(result)
        self.latest_callback_result = result

    def set_wait(self, result):
        super(WaitCallback, self).set_wait(result)
        self.latest_callback_result = result

    def wait(self):
        r = super(WaitCallback, self).wait()
        if self.return_callback_result:
            return self.latest_callback_result
        else:
            return r


def wait_for_callback(callback, **kwargs):
    """
    wait for a callback function to return Truthy,
    if it returns Falsey then we fail, (override with no_fail=True)
    if it returns None then we keep waiting
    :param callback: callback function
    :param kwargs:
    :return:
    """
    return WaitCallback(callback, **kwargs).wait()


def wait_for_callback_value(callback, value, **kwargs):
    """
    wait for a callback function to return value(s)
    if it returns anything else then we keep waiting (override with no_fail=False)
    :param callback: callback function
    :param value: waiting for value(s)
    :param kwargs:
    :return:
    """
    ready_values = value if isinstance(value, list) else [value]
    kwargs.setdefault('ready_values', ready_values)
    kwargs.setdefault('no_fail', True)
    return WaitCallback(callback, **kwargs).wait()


def wait(**kwargs):
    """
    function to call WaitLib
    :param kwargs: kwargs for waitlib
    :return:
    """
    return WaitLib(**kwargs)


__all__ = ['wait_for_callback', 'wait', 'WaitStatus']
