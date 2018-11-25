#! /usr/bin/env python

# Standard Imports
import unittest
import time

# irtools Imports
from irtools import *
from irtools._libs import wait_utils
from irtools.kits import taskmanager

# Logging
log = logging.getLogger('irtools.lib_tests.wait_utils')
utils.logging_setup(level=0, log_file=ir_log_dir + '/test_lib_wait_utils.log')


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


