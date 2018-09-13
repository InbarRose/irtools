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
        delays = [randrange(3, 7) for _ in range(50)]

        log.debug('mapping to thread pool, starting')
        pool.map(self.wait_delay, delays)
        log.debug('mapping to thread pool, finished')

        self.assertEquals(50, pool.total_task_count)

        log.debug('waiting for thread pool completion, starting: current_count={} total={} remaining={}'.format(
            pool.current_count, pool.total_task_count, pool.remaining_tasks))
        pool.wait_completion()
        log.debug('waiting for thread pool completion, finished')

        self.assertEquals(50, pool.current_count)
        self.assertEquals(0, pool.remaining_tasks)

    def test_add_wait_finished(self):
        # Instantiate a thread pool with 5 worker threads
        log.debug('creating thread pool')
        pool = thread_pool.ThreadPool(5)

        # Generate random delays
        log.debug('adding tasks to thread pool, starting')
        for _ in range(50):
            pool.add_task(self.wait_delay, randrange(3, 7))
        log.debug('adding tasks to thread pool, finished')

        self.assertEquals(50, pool.total_task_count)

        log.debug('waiting for thread pool to stop processing, starting: current_count={} total={} remaining={}'.format(
            pool.current_count, pool.total_task_count, pool.remaining_tasks))
        while pool.processing:
            pass
        log.debug('waiting for thread pool to stop processing, finished')

        self.assertEquals(50, pool.current_count)
        self.assertEquals(0, pool.remaining_tasks)
