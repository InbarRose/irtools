#! /usr/bin/env python

# Standard Imports
from Queue import Queue
from threading import Thread

# irtools Imports
from irtools import *

# Logging
log = logging.getLogger('irtools.kits.thread_pool')

# Ideas was originally taken from https://www.metachris.com/2016/04/python-threadpool/ and modified heavily


class Worker(Thread):
    """ Thread executing tasks from a given tasks queue """
    def __init__(self, worker_id, task_queue, parent_pool):
        super(Worker, self).__init__()
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.parent_pool = parent_pool
        self.daemon = True
        self.start()
        self.trace_logs = False

    def run(self):
        while True:
            func, args, kwargs = self.task_queue.get()
            if self.trace_logs:
                log.trace('worker starting task: worker-id={} func={}'.format(self.worker_id, func))
            try:
                func(*args, **kwargs)
            except Exception as exc:
                log.error('Exception in thread: worker-id={} func={} exc={}'.format(self.worker_id, func, exc),
                          exc_info=True)
                self.parent_pool.task_nok(self.worker_id)
            else:
                self.parent_pool.task_ok(self.worker_id)
            finally:
                # Mark this task as done, whether an exception happened or not
                self.task_queue.task_done()


class ThreadPool(object):
    """ Pool of threads consuming tasks from a queue """
    def __init__(self, num_threads, worker_class=None, max_queue_size=0):
        self.tasks = Queue(max_queue_size)
        self.total_task_count = 0
        self.tasks_ok_count = 0
        self.tasks_nok_count = 0
        self.worker_counters = {}
        self._workers = {}
        self._worker_class = worker_class or Worker
        for i in range(num_threads):
            self._add_worker(i)

    def _add_worker(self, worker_id, raise_on_id_clash=False):
        if worker_id in self._workers:
            if raise_on_id_clash:
                raise Exception('worker with that id already exists', worker_id)
        worker = self._worker_class(worker_id=worker_id, task_queue=self.tasks, parent_pool=self)
        self._workers[worker_id] = worker
        self.worker_counters[worker_id] = 0

    @property
    def current_count(self):
        return sum(self.worker_counters.values())

    @property
    def remaining_tasks(self):
        return self.total_task_count - self.current_count

    @property
    def all_workers_started(self):
        return all(self.worker_counters.values())

    @property
    def any_workers_started(self):
        return any(self.worker_counters.values())

    def _increment_worker_count(self, worker_id):
        self.worker_counters[worker_id] += 1

    def task_ok(self, worker_id):
        self._increment_worker_count(worker_id)
        self.tasks_ok_count += 1

    def task_nok(self, worker_id):
        self._increment_worker_count(worker_id)
        self.tasks_nok_count += 1

    def add_task(self, func, *args, **kwargs):
        """ Add a task to the queue """
        self.tasks.put((func, args, kwargs))
        self.total_task_count += 1

    def map(self, func, args_list):
        """ Add a list of tasks to the queue """
        # Add the jobs in bulk to the thread pool. Alternatively you could use
        # `add_task` to add single jobs. The code will block here, which
        # makes it possible to cancel the thread pool with an exception when
        # the currently running batch of workers is finished.
        for args in args_list:
            self.add_task(func, args)

    @property
    def finished(self):
        """are all tasks complete (based on count)"""
        return bool(self.remaining_tasks == 0)

    @property
    def processing(self):
        """are tasks still being processed"""
        return not self.finished

    def wait_completion(self):
        """ Wait for completion of all the tasks in the queue BLOCKING """
        self.tasks.join()
