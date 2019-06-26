#! /usr/bin/env python

# Standard Imports
import unittest
import time
import datetime

# irtools Imports
from irtools import *
from irtools._libs import wait_utils
from irtools.kits import taskmanager

# Logging
log = logging.getLogger('irtools.lib_tests.wait_utils')
utils.logging_setup(level=0, log_file=ir_log_dir + '/test_lib_wait_utils.log')


def gen_time_passed_since_time_func(since, passed):
    return lambda: bool(time.time() - since > passed)


class TestWait(unittest.TestCase):

    def test_wait_callable(self):
        # setup
        tm = taskmanager.TaskManager('waitTask')
        tm.add_task(taskmanager.Task('sleep5', time.sleep, fargs=[5]))
        waiter = wait_utils.WaitCallback(lambda: tm.all_tasks_finished,
                                         no_fail=True, log_trace=True,
                                         return_wait_status=True,
                                         period=0.5)
        # start timer then wait
        tm.go_no_wait()
        status = waiter.wait()
        # check results
        self.assertEquals(wait_utils.WaitStatus.ready, status)
        self.assertGreater(waiter.elapsed_time, 4)
        self.assertLess(waiter.elapsed_time, 6)
        self.assertTrue(waiter.result)
        self.assertIsNone(waiter.error)

    def test_timeout_seconds(self):
        waiter = wait_utils.WaitLib(ready_method=lambda: False,
                                    timeout=2, no_fail=True, log_trace=True, raise_on_timeout=False)
        waiter.wait()
        self.assertEquals(wait_utils.WaitStatus.timeout, waiter.status)

    def test_timeout_datetime(self):
        waiter = wait_utils.WaitLib(ready_method=lambda: False,
                                    timeout=datetime.datetime.now() + datetime.timedelta(seconds=2),
                                    no_fail=True, log_trace=True, raise_on_timeout=False)
        waiter.wait()
        self.assertEquals(wait_utils.WaitStatus.timeout, waiter.status)

    def test_wait_until(self):
        dt_start = datetime.datetime.now()
        dt_in_2_seconds = dt_start + datetime.timedelta(seconds=2)
        wait_utils.wait_until_datetime(dt_in_2_seconds)
        dt_end = datetime.datetime.now()
        duration = dt_end - dt_start
        self.assertAlmostEqual(
            (dt_in_2_seconds - datetime.datetime(1970, 1, 1)).total_seconds(),
            (dt_end - datetime.datetime(1970, 1, 1)).total_seconds(),
            delta=1
        )
        self.assertAlmostEqual(2, duration.total_seconds(), places=2)

    def test_sleep_until(self):
        dt_start = datetime.datetime.now()
        dt_in_2_seconds = dt_start + datetime.timedelta(seconds=2)
        wait_utils.sleep_until_datetime(dt_in_2_seconds)
        dt_end = datetime.datetime.now()
        duration = dt_end - dt_start
        self.assertAlmostEqual(
            (dt_in_2_seconds - datetime.datetime(1970, 1, 1)).total_seconds(),
            (dt_end - datetime.datetime(1970, 1, 1)).total_seconds(),
            delta=1
        )
        self.assertAlmostEqual(2, duration.total_seconds(), places=2)

    def test_wait_for_all(self):
        start = time.time()
        conditions = [
            gen_time_passed_since_time_func(start, 0.1),
            gen_time_passed_since_time_func(start, 0.5),
            gen_time_passed_since_time_func(start, 1.0),
            gen_time_passed_since_time_func(start, 1.2),
            gen_time_passed_since_time_func(start, 1.7),
            gen_time_passed_since_time_func(start, 2.0),
        ]
        r = wait_utils.wait_for_all(*conditions, period=0.1)
        end = time.time()
        self.assertTrue(r)
        self.assertLessEqual(2, end-start)
        self.assertListEqual([True] * 6, [c() for c in conditions[:]])

    def test_wait_for_any(self):
        start = time.time()
        conditions = [
            gen_time_passed_since_time_func(start, 0.1),
            gen_time_passed_since_time_func(start, 0.5),
            gen_time_passed_since_time_func(start, 1.0),
            gen_time_passed_since_time_func(start, 1.2),
            gen_time_passed_since_time_func(start, 1.7),
            gen_time_passed_since_time_func(start, 2.0),
        ]
        r = wait_utils.wait_for_any(*conditions, period=0.1)
        end = time.time()
        self.assertTrue(r)
        self.assertLessEqual(0.1, end-start)
        self.assertListEqual([False]*5, [c() for c in conditions[1:]])

    def test_wait_for_any_n(self):
        start = time.time()
        conditions = [
            gen_time_passed_since_time_func(start, 0.1),
            gen_time_passed_since_time_func(start, 0.5),
            gen_time_passed_since_time_func(start, 1.0),
            gen_time_passed_since_time_func(start, 1.2),
            gen_time_passed_since_time_func(start, 1.7),
            gen_time_passed_since_time_func(start, 2.0),
        ]
        r = wait_utils.wait_for_any_n(*conditions, n=3, period=0.1)
        end = time.time()
        self.assertTrue(r)
        self.assertLessEqual(1.0, end-start)
        self.assertListEqual([True]*3 + [False]*3, [c() for c in conditions[:]])
