#! /usr/bin/env python

# Standard Imports
import unittest
from random import randrange
import time

# irtools Imports
from irtools import *
from irtools.kits import taskmanager

# Logging
log = logging.getLogger('irtools.tests.taskmanager')
utils.logging_setup(level=0, log_file=ir_log_dir + '/test_taskmanager.log')


# TESTING

def _log(text):
    log.trace('test-method|log: text={}'.format(text))


def _loop_log_wait(text, loop, wait):
    for i in range(loop):
        log.trace('test-method|loop_log_wait: text={} loop={} wait={}'.format(text, i, wait))
        time.sleep(wait)


def _make_task_tree_alpha():
    """
    task tree alpha
    (diagram made online with http://asciiflow.com/)

    +------+
    |task_1|
    +------+
        |
    +---v--+
    |task_2|
    +------+
        |
    +---v--+  +------+
    |task_3+->+task_4+----------------------------------------------------------+
    +------+  +------+                                                          |
          |                                                                     |
          |   +--------+  +--------+  +--------+                                |
          +-->+task_a_1+->+task_a_2+->+task_a_3|                     +--------+ |
          |   +--------+  +--------+  +--------+                   ->+task_f_1| |
          |           |           +---->                           | +--------+ |
          |           |                |                           |  ^      |  |
          |           |   +--------+   |  +--------+               |  |      |  |
          |           +--->task_c_1+----->+task_d_1|               |  |      |  |
          |           |   +--------+   |  +--------+               |  |      |  |
          |           |                |          |   +----------+ |  |      |  |
          |           +------------------------------>+task_e_1_a+-+  |      |  |
          |           |                |          |   +----------+    |      |  |
          |           |                |          |                   |      |  |
          |           |                |          |   +----------+    |      |  |
          |           +------------------------------>+task_e_1_b+----+      |  |
          |           |                |              +----------+           |  |
          |           |                |                                     |  |
          |           |               +v-------+                      +------+  |
          |           |           +-->+task_c_2+--------------+       |         |
          |           |           |   +--------+              |       |         |
          |           |           |                           |  +----v---+     |
          |   +--------+  +--------+  +--------+              +-->task_g_1<-----+
          +-->+task_b_1+->+task_b_2+->+task_b_3|                 +--------+
              +--------+  +--------+  +--------+

    :return:
    """
    task_tree = {
        'task_1': set(),
        'task_2': {'task_1'},
        'task_3': {'task_2'},
        'task_a_1': {'task_3'},
        'task_b_1': {'task_3'},
        'task_a_2': {'task_a_1'},
        'task_a_3': {'task_a_2'},
        'task_b_2': {'task_b_1'},
        'task_b_3': {'task_b_2'},
        'task_c_1': {'task_a_1', 'task_b_1'},
        'task_c_2': {'task_a_2', 'task_b_2'},
        'task_d_1': {'task_c_1'},
        'task_e_1_a': {'task_d_1', 'task_a_1'},
        'task_e_1_b': {'task_d_1', 'task_b_1'},
        'task_f_1': {'task_e_1_a', 'task_e_1_b'},
        'task_4': {'task_3'},
        'task_g_1': {'task_4', 'task_f_1', 'task_c_2'},
    }
    return task_tree


class TestTaskManager(unittest.TestCase):

    def test_task_order_tree_alpha(self):
        tm = taskmanager.TaskManager('test_task_order_tree_alpha')

        expected_tasks_order = _make_task_tree_alpha()
        for task_name, task_reqs in expected_tasks_order.items():
            tm.add_task(taskmanager.Task(name=task_name, func=utils.noop, reqs=task_reqs))

        tasks_and_reqs = {t.name: t.reqs for t in tm.tasks.values()}
        self.assertDictEqual(expected_tasks_order, tasks_and_reqs)

        first_wave = tm._get_ready_tasks()
        self.assertEquals(['task_1'], first_wave)
        for task_name in first_wave:
            tm.tasks[task_name].finished = True

        second_wave = tm._get_ready_tasks()
        self.assertEquals(['task_2'], second_wave)
        for task_name in second_wave:
            tm.tasks[task_name].finished = True

        third_wave = tm._get_ready_tasks()
        self.assertEquals(['task_3'], third_wave)
        for task_name in third_wave:
            tm.tasks[task_name].finished = True

        fourth_wave = tm._get_ready_tasks()
        self.assertEquals(sorted(['task_4', 'task_a_1', 'task_b_1']), sorted(fourth_wave))
        for task_name in fourth_wave:
            tm.tasks[task_name].finished = True

        fifth_wave = tm._get_ready_tasks()
        self.assertEquals(sorted(['task_a_2', 'task_b_2', 'task_c_1']), sorted(fifth_wave))
        for task_name in fifth_wave:
            tm.tasks[task_name].finished = True

        sixth_wave = tm._get_ready_tasks()
        self.assertEquals(sorted(['task_a_3', 'task_b_3', 'task_c_2', 'task_d_1']), sorted(sixth_wave))
        for task_name in sixth_wave:
            tm.tasks[task_name].finished = True

        seventh_wave = tm._get_ready_tasks()
        self.assertEquals(sorted(['task_e_1_a', 'task_e_1_b']), sorted(seventh_wave))
        for task_name in seventh_wave:
            tm.tasks[task_name].finished = True

        eighth_wave = tm._get_ready_tasks()
        self.assertEquals(sorted(['task_f_1']), sorted(eighth_wave))
        for task_name in eighth_wave:
            tm.tasks[task_name].finished = True

        ninth_wave = tm._get_ready_tasks()
        self.assertEquals(sorted(['task_g_1']), sorted(ninth_wave))
        for task_name in ninth_wave:
            tm.tasks[task_name].finished = True

    def test_subtaskmanager(self):
        pass

    def test_convenience_ret_validation(self):
        pass

    def test_convenience_simple_tasklist_gen(self):
        tasklist = taskmanager.simple_task_list_gen(
            utils.noop,
            utils.noop,
            utils.noop,
            indexed=True
        )
        self.assertEquals(3, len(tasklist))
        expected_names = ['1_noop', '2_noop', '3_noop']
        names = [t.name for t in tasklist]
        self.assertEquals(expected_names, names)

    def test_convenience_flat_manager(self):
        tasklist = taskmanager.simple_task_list_gen(
            utils.noop,
            utils.noop,
            utils.noop,
            indexed=True
        )
        tm = taskmanager.create_flat_manager('test_convenience_flat_manager', *tasklist)
        ready_tasks = tm._get_ready_tasks()
        self.assertEquals(sorted([t.name for t in tasklist]), sorted(ready_tasks))

    def test_convenience_serialized_manager(self):
        tasklist = taskmanager.simple_task_list_gen(
            utils.noop,
            utils.noop,
            utils.noop,
            indexed=True
        )
        tm = taskmanager.create_serialized_manager('test_convenience_serialized_manager', *tasklist)
        ready_tasks = tm._get_ready_tasks()
        self.assertEquals(1, len(ready_tasks))
        self.assertEquals(sorted([t.name for t in tasklist])[0], ready_tasks[0])
        first_task = tm.tasks['1_noop']
        second_task = tm.tasks['2_noop']
        third_task = tm.tasks['3_noop']
        self.assertFalse(first_task.reqs)
        self.assertEquals({'1_noop'}, second_task.reqs)
        self.assertEquals({'2_noop'}, third_task.reqs)

    def test_sanity(self):
        tm = taskmanager.TaskManager('test_sanity')

        tm.add_task(taskmanager.Task(name='test_1', func=_log, fargs=['test_1']))
        tm.add_task(taskmanager.Task(name='test_2', reqs='test_1', func=_loop_log_wait, fargs=['test_2', 2, 1]))
        tm.add_task(taskmanager.Task(name='test_3', reqs='test_1', func=_log, fargs=['test_3']))
        tm.add_task(taskmanager.Task(name='test_4', reqs='test_2', func=_loop_log_wait, fargs=['test_4', 5, 1],
                                     active=False))
        tm.add_task(taskmanager.Task(name='test_5', reqs='test_1', func=_loop_log_wait, fargs=['test_5', 10, 1]))
        tm.add_task(taskmanager.Task(name='test_6', reqs='test_3 test_4', func=_loop_log_wait, fargs=['test_6', 2, 3]))
        tm.add_task(
            taskmanager.Task(name='test_7', reqs='test_6 test_5', func=_loop_log_wait, fargs=['test_7', 5, 1],
                             active=False))
        tm.add_task(taskmanager.Task(name='test_8', reqs='test_7', func=_loop_log_wait, fargs=['test_8', 5, 1]))
        tm.add_task(taskmanager.Task(name='test_9', reqs='test_8 test_7', func=_loop_log_wait, fargs=['test_9', 5, 1]))

        tm.go()

        log.info('test_sanity task_rcs: {}'.format(tm.task_rcs))
        self.assertEquals(0, tm.worst_rc)
        expected_task_rcs = {'test_6': 0, 'test_5': 0, 'test_3': 0, 'test_2': 0, 'test_1': 0, 'test_9': 0, 'test_8': 0}
        self.assertEquals(expected_task_rcs, tm.task_rcs)

    def test_subsanity(self):
        # make subtaskmanager
        stm = taskmanager.SubTaskManager('test_subsanity_child')
        stm.add_task(taskmanager.Task(name='test_1', func=_log, fargs=['test_1']))
        stm.add_task(taskmanager.Task(name='test_2', reqs='test_1', func=_loop_log_wait, fargs=['test_2', 2, 1]))
        stm.add_task(taskmanager.Task(name='test_3', reqs='test_1', func=_log, fargs=['test_3']))
        stm.add_task(taskmanager.Task(name='test_4', reqs='test_2', func=_loop_log_wait, fargs=['test_4', 5, 1],
                                      active=False))
        stm.add_task(taskmanager.Task(name='test_5', reqs='test_1', func=_loop_log_wait, fargs=['test_5', 10, 1]))
        stm.add_task(taskmanager.Task(name='test_6', reqs='test_3 test_4', func=_loop_log_wait, fargs=['test_6', 2, 3]))
        stm.add_task(
            taskmanager.Task(name='test_7', reqs='test_6 test_5', func=_loop_log_wait, fargs=['test_7', 5, 1],
                             active=False))
        stm.add_task(taskmanager.Task(name='test_8', reqs='test_7', func=_loop_log_wait, fargs=['test_8', 5, 1]))
        stm.add_task(taskmanager.Task(name='test_9', reqs='test_8 test_7', func=_loop_log_wait, fargs=['test_9', 5, 1]))

        # make parent taskmanager
        tm = taskmanager.TaskManager('test_subsanity_parent')
        tm.add_task(taskmanager.Task(name='task1', func=_loop_log_wait, fargs=['task1', 2, 1]))
        tm.add_task(taskmanager.SubManagerTask(name='sub', manager=stm, reqs='task1'))
        tm.add_task(taskmanager.Task(name='task2', func=_loop_log_wait, fargs=['task2', 2, 1], reqs='sub'))
        tm.add_task(taskmanager.Task(name='task3', func=_loop_log_wait, fargs=['task3', 2, 1], reqs='task1'))

        tm.go()

        log.info('test_subsanity task_rcs: {}'.format(tm.task_rcs))
        self.assertEquals(0, tm.worst_rc)
        expected_task_rcs = {'task1': 0, 'task2': 0, 'task3': 0, 'sub': 0}
        self.assertEquals(expected_task_rcs, tm.task_rcs)

    def test_wait_timeout(self):
        tm = taskmanager.TaskManager('test_wait_timeout')
        tm.add_task(taskmanager.Task(name='sleep_10', func=time.sleep, fargs=[10]))
        tm.go_no_wait()
        r = tm.wait(timeout=2, raise_on_timeout=False, return_wait_status=True)
        self.assertEquals(utils.WaitStatus.timeout, r)

    def test_wait(self):
        tm = taskmanager.TaskManager('test_wait')
        tm.add_task(taskmanager.Task(name='sleep_2', func=time.sleep, fargs=[2]))
        tm.go_no_wait()
        r = tm.wait(raise_on_timeout=False, return_wait_status=True)
        self.assertEquals(utils.WaitStatus.ready, r)
