#! /usr/bin/env python

# Standard Imports
import time
import uuid
import datetime

# irtools Imports
from irtools import *
from enum_utils import enum
from datetime_utils import seconds_to_future

# logging
log = logging.getLogger('irtools.utils.wait')

WaitStatus = enum(ready='READY', wait='WAIT', fail='FAIL', timeout='TIMEOUT', error='ERROR')


class WaitLib(object):
    """wait for something, supports ready, fail, and wait function calls to check status"""

    _default_timeout = 120     # default timeout (2 minutes)
    _default_period = 1      # default wait 1 second between checks
    _default_grace_time = 0  # default don't wait before starting to check
    _default_ready_values = None  # None - default behaviour (truthy = ready) / else contains result
    _default_fail_values = None   # None - default behaviour (falsey = fail) / else contains result
    _default_wait_values = None   # None - default behaviour (None = wait) / else contains result

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
        assert isinstance(self.timeout, (int, datetime.datetime))
        self._timeout_seconds = None
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
        self.check_fail_method = kwargs.pop('fail_method', None)
        self.check_fail_values = kwargs.pop('fail_values', self._default_fail_values)
        self.check_wait_method = kwargs.pop('wait_method', None)
        self.check_wait_values = kwargs.pop('wait_values', self._default_wait_values)
        assert callable(self.check_ready_method)
        assert callable(self.check_fail_method) or self.check_fail_method is None
        assert callable(self.check_wait_method) or self.check_wait_method is None
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
            # add user-designated ID
            parts.append('id={}'.format(self.identification))
        # if there are no other ID's add the UUID
        if not parts:
            parts.append('uuid={}'.format(self._uuid))
        # finally, add timeout
        if self.timeout:
            parts.append('timeout={}'.format(self.timeout))
        return parts

    def _check_timeout_valid(self):
        if isinstance(self.timeout, datetime.datetime):
            # timeout given as a datetime (should be in the future) convert to seconds
            log.debug('wait converting datetime timeout to seconds: {}'.format(self.wait_id))
            self._timeout_seconds = seconds_to_future(self.timeout, round_up=True, raise_on_past=True)
        elif isinstance(self.timeout, int):
            self._timeout_seconds = self.timeout
        else:
            raise RuntimeError(
                'wait unexpected error, bad type for timeout: {}'.format(self.wait_id),
                type(self.timeout), self.timeout
            )

        if self._timeout_seconds < self.grace_time + self.period:
            raise RuntimeError(
                'wait timeout is too short, not enough time for a single check!?: {}'.format(self.wait_id)
            )

    def wait(self):
        self._check_timeout_valid()
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
            if self.log_trace:
                log.trace('wait sleeping period: {} period={}'.format(self.wait_id, self.period))
            time.sleep(self.period)

    def get_status(self):
        if not self.is_wait:
            # status already set
            return self.status
        if self.log_trace:
            log.trace('wait checking status: {} elapsed={}'.format(self.wait_id, self.elapsed_time))
        # check the status
        self.check_ready()
        if self.is_ready:
            return self.status
        self.check_fail()
        if self.is_fail:
            return self.status
        self.check_timeout()
        if self.is_timeout:
            return self.status
        self.check_wait()  # run checks for wait?
        if self.is_wait:
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
            if self._is_ready_result(r):
                if self.log_process:
                    log.debug('wait Ready: {} r={}'.format(self.wait_id, r))
                self.set_ready(r)

    def _is_ready_result(self, result):
        # if no ready values supplied, then we check if result has a truthy value
        if self.check_ready_values is None and bool(result) is True:
            return True
        # if ready values are supplied, we check that the result is one of them
        if isinstance(self.check_ready_values, (list, tuple, set)) and result in self.check_ready_values:
            return True
        # if none of conditions were met, then it is not ready
        return False

    def check_fail(self):
        if self.no_fail:
            return
        if self.check_fail_method is None:
            return  # we don't have a fail method, we just wait
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
            if self._is_fail_result(r):
                if self.log_process:
                    log.debug('wait Fail: {} r={}'.format(self.wait_id, r))
                self.set_fail(r)

    def _is_fail_result(self, result):
        # if no fail values supplied, then we check if result has a falsey value
        if self.check_fail_values is None and bool(result) is False:
            return True
        # if fail values are supplied, we check that the result is one of them
        if isinstance(self.check_fail_values, (list, tuple, set)) and result in self.check_fail_values:
            return True
        # if none of conditions were met, then it is not fail
        return False

    def check_wait(self):
        # this whole method might be unnecessary (since we should keep waiting until ready/timeout/fail anyway)
        if self.check_wait_method is None:
            return  # we don't have a wait method, we just wait
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
            if self._is_wait_result(r):
                if self.log_process:
                    log.debug('wait Waiting: {} r={}'.format(self.wait_id, r))
                self.set_wait(r)

    def _is_wait_result(self, result):
        # if no wait values supplied, then we check if result has a None value
        if self.check_wait_values is None and result is None:
            return True
        # if wait values are supplied, we check that the result is one of them
        if isinstance(self.check_wait_values, (list, tuple, set)) and result in self.check_wait_values:
            return True
        # if none of conditions were met, then it is not fail
        return False

    def check_timeout(self):
        if self.log_trace:
            log.trace('wait checking for timeout: {} timeout={}'.format(self.wait_id, self.timeout))
        if self.timeout and self.elapsed_time > self._timeout_seconds:
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
        super(WaitCallback, self).__init__(**kwargs)

    def set_ready(self, result):
        super(WaitCallback, self).set_ready(result)
        self.latest_callback_result = result

    def set_fail(self, result):
        super(WaitCallback, self).set_fail(result)
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


def wait_for_ready_or_fail(ready_callback, fail_callback, **kwargs):
    """
    wait for a callback function to return True,
    if ready_callback returns True then we are ready
    if fail_callback returns True then we fail
    :param ready_callback: callback function
    :param fail_callback: callback function
    :param kwargs:
    :return:
    """
    kwargs.setdefault('fail_values', [True])
    kwargs.setdefault('ready_values', [True])
    return WaitLib(ready_method=ready_callback, fail_method=fail_callback, **kwargs).wait()


def wait(**kwargs):
    """
    function to call WaitLib
    :param kwargs: kwargs for waitlib
    :return:
    """
    return WaitLib(**kwargs)


def wait_for_files_to_exist(*files, **kwargs):
    """
    wait for all files to exist
    :param files: files to wait for
    :param kwargs: kwargs for waitlib
    :return:
    """

    def check_paths_exist(paths=files):
        return all(map(os.path.exists, paths))

    return WaitLib(ready_method=check_paths_exist, **kwargs).wait()


def wait_until_datetime(dt_wait, **kwargs):
    """
    sleep until a given datetime
    :param dt_wait: the datetime to wait for
    :param kwargs: kwargs for waitlib
    :return:
    """
    assert isinstance(dt_wait, datetime.datetime)
    dt_now = datetime.datetime.now()
    assert dt_wait > dt_now, 'wait time is in the past'

    def check_datetime_reached(datetime_to_reach=dt_wait):
        return bool(datetime.datetime.now() > datetime_to_reach)

    return WaitLib(ready_method=check_datetime_reached, **kwargs).wait()


def sleep_until_datetime(dt_wait):
    """
    sleep until a given datetime
    :param dt_wait: the datetime to wait for
    :return:
    """
    assert isinstance(dt_wait, datetime.datetime)
    dt_now = datetime.datetime.now()
    assert dt_wait > dt_now, 'wait time is in the past'
    td_for_wait = dt_wait - dt_now
    wait_time = td_for_wait.total_seconds()
    log.debug('waiting until datetime: timedelta={} seconds={}'.format(td_for_wait, wait_time))
    time.sleep(wait_time)


__all__ = [
    'wait_for_callback', 'wait_for_callback_value',
    'wait_for_ready_or_fail',
    'wait_for_files_to_exist',
    'wait', 'WaitStatus',
    'sleep_until_datetime', 'wait_until_datetime',
]
