#! /usr/bin/env python

# Standard Imports
import unittest
from random import randrange
import time

# irtools Imports
from irtools import *
from irtools.kits import thread_pool

# Logging
log = logging.getLogger('irtools.tests.thread_pool')
utils.logging_setup(level=0, log_file=ir_log_dir + '/test_thread_pool.log')


class TestThreadPool(unittest.TestCase):

    @staticmethod
    def wait_delay(seconds):
        # Function to be executed in a thread for testing
        log.trace("sleeping: seconds={}".format(seconds))
        time.sleep(seconds)

    def test_map_wait_completion(self):
        # Instantiate a thread pool with 5 worker threads
        log.debug('creating thread pool')
        pool = thread_pool.ThreadPool(5)

        # Generate random delays
        delays = [randrange(1, 3) for _ in range(50)]

        log.debug('mapping to thread pool, starting')
        pool.map(self.wait_delay, delays)
        log.debug('mapping to thread pool, finished')

        self.assertEquals(50, pool._total_task_count)

        log.debug('waiting for thread pool completion, starting: current_count={} total={} remaining={}'.format(
            pool.count_completed, pool._total_task_count, pool.count_remaining))
        pool.wait_completion()
        log.debug('waiting for thread pool completion, finished')

        self.assertEquals(50, pool.count_completed)
        self.assertEquals(0, pool.count_remaining)

    def test_add_wait_finished(self):
        # Instantiate a thread pool with 5 worker threads
        log.debug('creating thread pool')
        pool = thread_pool.ThreadPool(5)

        # Generate random delays
        log.debug('adding tasks to thread pool, starting')
        for _ in range(50):
            pool.add_task(self.wait_delay, randrange(1, 3))
        log.debug('adding tasks to thread pool, finished')

        self.assertEquals(50, pool._total_task_count)

        log.debug('waiting for thread pool to stop processing, starting: current_count={} total={} remaining={}'.format(
            pool.count_completed, pool._total_task_count, pool.count_remaining))
        while pool.processing:
            pass
        log.debug('waiting for thread pool to stop processing, finished')

        self.assertEquals(50, pool.count_completed)
        self.assertEquals(0, pool.count_remaining)
