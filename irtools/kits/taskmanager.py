#! /usr/bin/env python

#  Standard Imports
import time
from optparse import OptionParser
from collections import OrderedDict
from threading import Thread

# irtools Imports
from irtools import *

log = logging.getLogger('irtools.kits.taskmanager')


class TaskException(RuntimeError):
    pass


class InvalidReturnException(TaskException):
    pass


class TaskManagerException(RuntimeError):
    pass


class DuplicateTaskException(TaskManagerException):
    pass


class MissingTaskReferenceException(TaskManagerException):
    pass


class AbstractTask(object):

    msg_starting = 'Task starting'
    msg_finishing = 'Task finishing'
    msg_func_exception = 'Task Func Exception'

    def __init__(self, name, func, fargs=None, fkwargs=None, **kwargs):
        """
        Initializes a new Task
        :param name:
        :param func:
        :param fargs:
        :param fkwargs:
        :param kwargs:
        """
        # fix None fargs and fkwargs as empty list/dict
        fargs = fargs or []
        fkwargs = fkwargs or {}

        # verify critical params
        assert isinstance(name, str)
        assert callable(func)
        assert (fargs is None) or isinstance(fargs, (list, tuple))
        assert (fkwargs is None) or isinstance(fkwargs, dict)

        # store parameters
        self.name = name
        self.func = func
        self.fargs = fargs
        self.fkwargs = fkwargs

        # optional parameters
        self.timeout = kwargs.pop('timeout', False)
        self.kill_callback = kwargs.pop('kill_callback', None)
        if self.kill_callback:
            assert callable(self.kill_callback)
        self.ret_validation = kwargs.pop('ret_validation', None)
        if self.ret_validation:
            assert callable(self.ret_validation)
        self._run_as_daemon = kwargs.pop('run_as_daemon', True)
        self.announce_as_trace = kwargs.pop('announce_as_trace', False)

        # store extra kwargs
        self.kwargs = kwargs

        # runtime variables
        self.start_time = 0
        self.end_time = 0
        self.elapsed_time = 0
        self.was_run = False
        self.operating = False
        self.finished = False
        self.thread = None

        # members that get updated later
        self.task_manager = None
        self.ret = None
        self.messages = []

    def attach_manager(self, task_manager):
        """
        attach a task manager to this task
        (this is a very important step that is called when the task is added to a manager, usually right after creation)
        :param task_manager: the TaskManager object that will manage this Task
        :return:
        """
        self.task_manager = task_manager

    def _to_json(self):
        """
        return a dict of some members
        :return:
        """
        return {
            # parameters
            'name': self.name,
            # optional parameters
            'timeout': self.timeout,
            # runtime variables
            'start_time': self.start_time,
            'end_time': self.end_time,
            'elapsed_time': self.elapsed_time,
            'was_run': self.was_run,
            'operating': self.operating,
            'finished': self.finished,
            # members
            'messages': self.messages,
        }

    def check_timeout(self):
        """
        Checks if this task has reached it's timeout.
        :return:
        """
        if self.start_time == 0:
            # task not started yet
            return False

        # convert timeout to int / converts False to 0
        timeout = int(self.timeout)

        if not timeout and self.task_manager:
            # check if there is a default timeout if our timeout is 0/False
            timeout = self.task_manager.default_task_timeout

        if not timeout:
            # there is no timeout possible for this task
            return False

        # get the elapsed time and compare to timeout
        self.elapsed_time = time.time() - self.start_time
        return bool(self.elapsed_time > timeout)

    def kill_task(self):
        """
        attempts to kill this task
        :return:
        """
        if self.kill_callback is not None and callable(self.kill_callback):
            r = self.kill_callback(self)
        elif self.task_manager and callable(self.task_manager.default_kill_callback):
            r = self.task_manager.default_kill_callback(self)
        else:
            r = None
        # todo: finish handling?
        return r

    @property
    def run_as_daemon(self):
        """
        determines if this task should be run as a Daemon or a regular thread
        :return:
        """
        if self._run_as_daemon:
            return True
        elif self.task_manager:
            return self.task_manager.run_tasks_as_daemons
        else:
            return False

    def go(self, dry_run):
        """
        main function to start the Task
        checks how to run the task and then runs it (what kind of thread)
        :param dry_run:
        :return:
        """
        if self.operating:
            raise TaskException('Task already operating', self)
        t = Thread(target=self.go_wait, args=[dry_run])
        if self.run_as_daemon:
            t.daemon = True
        self.thread = t
        self.thread.start()

    def _start(self):
        """
        called at the start of the operating of the func
        :return:
        """
        self.announce(log.info, self.msg_starting, timeout=self.timeout)
        self.operating = True
        self.was_run = True
        self.start_time = time.time()

    def _finish(self):
        """
        called at the end of the operating of the func
        :return:
        """
        self.end_time = time.time()
        self.elapsed_time = int(self.end_time - self.start_time)
        self.operating = False
        self.finished = True
        self._announce_finishing()
        self._report_task_finished_to_manager()

    def _announce_finishing(self):
        """
        how we announce that we are finished with a task
        :return:
        """
        self.announce(log.info, self.msg_finishing, time=self.elapsed_time)

    def _report_task_finished_to_manager(self):
        """
        reports to the task manager that this task is finished
        the task manager may do something with this information
        :return:
        """
        self.task_manager.handle_task_reports_finished(self)

    def go_wait(self, dry_run=False):
        """
        the actual go function, this should never be called directly when operating normally
        Runs the function and checks rc and makes announcements, handles cleanup and exceptions
        """
        self._start()
        try:
            if not dry_run:
                ret = self.trigger_func()
            else:
                return None
        except Exception as exc:
            self.handle_func_exception(exc)
        else:
            self.validate_ret(ret)
        finally:
            self._finish()
            return self.ret

    def trigger_func(self):
        """this is the actual function that the task triggers"""
        return self.func(*self.fargs, **self.fkwargs)

    def handle_func_exception(self, exc):
        """
        function that handles func exceptions
        :param exc: the exception encountered
        :return:
        """
        self.announce(log.error, self.msg_func_exception, exc=exc, exc_info=True)

    def validate_ret(self, ret):
        """
        function that performs validation (if any) on the ret that is returned by the func
        :param ret: the ret returned by the func
        :return:
        """
        if self.ret_validation is not None and callable(self.ret_validation):
            ret = self.ret_validation(ret)
        self.ret = ret
        return self.ret

    def announce(self, logfunc, announcement, exc_info=False, **kwargs):
        """
        make an announcement (log)
        :param logfunc: the log function to use log.trace log.debug log.info log.warn log.error
        :param announcement: the main body of the message
        :param exc_info: to include execution trace in the log or not
        :param kwargs: any kwargs to add to the announcement
        :return:
        """
        # make the message
        message = '{announcement}: {task} {kwargs}'.format(
            announcement=announcement,
            task=self.log_display,
            kwargs=' '.join(sorted(utils.convert_dict_params_to_list_of_string(kwargs)))
        )
        # store the message
        self.messages.append(message)

        # override the log function if needed
        if self.announce_as_trace or self.task_manager and self.task_manager.tasks_announce_trace:
            logfunc = log.trace

        # add "trace..." to message when logging execution trace
        if exc_info is True:
            message += ' trace...'

        # log the message
        logfunc(message, exc_info=exc_info)

    @property
    def log_display(self):
        """
        How we should display this task in the log messages (announcements)
        :return:
        """
        if self.task_manager:
            return "Task(name='{}' manager='{}')".format(self.name, self.task_manager.name)
        else:
            return "Task(name='{}')".format(self.name)

    def __str__(self):
        """representing the Task object as a string"""
        return self.log_display


class RCTask(AbstractTask):

    valid_rcs = {
        -1: 'timeout',
        0: 'okay',
        1: 'unstable',
        2: 'failure',
        3: 'errors',
        4: 'aborted',
    }

    replaceable_ret_values = {
        None: 0,
        True: 0,
        False: 0,
    }

    msg_replace_ret = 'Task got bad ret, ignoring and replacing'
    msg_invalid_rc = 'Task got invalid rc'
    msg_bad_rc = 'Task got bad rc'

    def __init__(self, name, func, fargs=None, fkwargs=None, **kwargs):
        super(RCTask, self).__init__(name, func, fargs, fkwargs, **kwargs)
        # runtime variables
        self.rc = None
        self.got_bad_rc = False

    def _announce_finishing(self):
        """
        announce the task is finishing, and include rc
        :return:
        """
        self.announce(log.info, self.msg_finishing, time=self.elapsed_time, rc=self.rc)

    def validate_ret(self, ret):
        """
        validate the return from the func call
        :param ret:
        :return:
        """
        # lets call the super
        ret = super(RCTask, self).validate_ret(ret)
        # then we attempt to convert the ret into an rc
        rc = self._get_rc_from_ret(ret)
        # lets dispatch to rc validation
        self.validate_rc(rc)

    def _get_rc_from_ret(self, ret):
        """
        attempts to convert a ret into an rc
        :param ret:
        :return:
        """
        # check if the ret matches any of the replaceable ret values
        # for None, True, False replaceable values we need to verify with identity "is"
        # for other replaceable values (possibly in the future) we use eq "=="
        # this prevents 1 or 0 from being converted because 0==False and 1==True
        if any(((ret is v) if utils.is_bool_or_none(v) else ret == v) for v in self.replaceable_ret_values):
            rc = self.replaceable_ret_values.get(ret)
            self.announce(log.warn, self.msg_replace_ret, ret=ret, rc=rc)
        elif hasattr(ret, 'rc'):
            rc = ret.rc
        else:
            rc = ret
        return rc

    def validate_rc(self, rc):
        """
        validates the rc returned from the func call
        :param rc:
        :return:
        """
        # now we verify it is a valid rc
        if not isinstance(rc, int) or rc not in self.valid_rcs:
            self.announce(log.error, self.msg_invalid_rc, rc=rc)
            raise InvalidReturnException(rc)
        # the rc is valid now store the rc
        self.rc = rc
        # check if good rc
        if rc != 0:
            # if it is not a good rc we need to handle it
            self.handle_bad_rc(rc)

    def handle_bad_rc(self, rc):
        """
        how we handle a bad rc returned from the func call
        :param rc:
        :return:
        """
        self.got_bad_rc = True
        self.announce(log.error, self.msg_bad_rc, rc=rc)

    def handle_func_exception(self, exc):
        """
        how we handle exceptions returned from the func call
        :param exc:
        :return:
        """
        super(RCTask, self).handle_func_exception(exc)
        self.validate_rc(3)


class OrderedTask(RCTask):
    def __init__(self, name, func, fargs=None, fkwargs=None, **kwargs):
        # parameters
        reqs = kwargs.pop('reqs', None)
        if isinstance(reqs, (list, set, tuple)):
            self.reqs = set(reqs)
        elif isinstance(reqs, str):
            self.reqs = set(reqs.split())
        elif reqs is None:
            self.reqs = set()
        else:
            raise TypeError('reqs must be None, tuple, set, list, or string with names of other task(s)')

        # optional parameters
        self.active = kwargs.pop('active', True)

        # runtime variables
        self.next_tasks = set()  # for debugging and logging, not used for flow logic

        # super
        super(OrderedTask, self).__init__(name, func, fargs, fkwargs, **kwargs)


class AbstractTaskManager(object):

    msg_duplicate_task_name = 'TaskManager already has a task with that name'
    msg_operating_halted = 'TaskManager operating loop halted'
    msg_task_timeout = 'TaskManager Task timed out, killing task, stopping'
    msg_duration_in_progress = 'TaskManager duration requested, in progress'
    msg_starting = 'TaskManager starting'
    msg_finishing = 'TaskManager finishing'
    msg_tasks_still_running = 'TaskManager still has running tasks'

    def __init__(self, name, **kwargs):
        # store parameters
        self.name = name

        # optional parameters
        self.dry_run = kwargs.pop('dry_run', False)
        self.default_task_timeout = kwargs.pop('default_task_timeout', 3600)
        self.default_kill_callback = kwargs.pop('default_kill_callback', utils.noop)
        self.tasks_announce_trace = kwargs.pop('tasks_announce_trace', False)
        self.announce_as_trace = kwargs.pop('announce_as_trace', False)
        self.run_tasks_as_daemons = kwargs.pop('run_tasks_as_daemons', False)
        self.stop_running_tasks_on_halt = kwargs.pop('stop_running_tasks_on_halt', False)
        self.report_still_running_tasks = kwargs.pop('report_still_running_tasks', True)

        # store extra kwargs
        self.kwargs = kwargs

        # runtime variables
        self.operating = False
        self.stop_operating = False
        self.finished = False
        self.start_time = 0
        self.end_time = 0

        # members
        self.tasks = OrderedDict()
        self.messages = []

    def announce(self, logfunc, announcement, exc_info=False, **kwargs):
        """
        make an announcement (log)
        :param logfunc: the log function to use log.trace log.debug log.info log.warn log.error
        :param announcement: the main body of the message
        :param exc_info: to include execution trace in the log or not
        :param kwargs: any kwargs to add to the announcement
        :return:
        """
        # make the message
        message = '{announcement}: {taskmanager} {kwargs}'.format(
            announcement=announcement,
            taskmanager=self.log_display,
            kwargs=' '.join(sorted(utils.convert_dict_params_to_list_of_string(kwargs)))
        )
        # store the message
        self.messages.append(message)

        # override the log function if needed
        if self.announce_as_trace:
            logfunc = log.trace

        # add "trace..." to message when logging execution trace
        if exc_info is True:
            message += ' trace...'

        # log the message
        logfunc(message, exc_info=exc_info)

    @property
    def log_display(self):
        """
        How we should display this TaskManager in the log messages (announcements)
        :return:
        """
        return "TaskManager(name='{}')".format(self.name)

    def __str__(self):
        """representing the TaskManager object as a string"""
        return self.log_display

    def add_task(self, task):
        """
        Add a task to the TaskManager
        will attach this TaskManger to the Task
        :param task: Task object to add to this TaskManager
        """
        if task.name in self.tasks.keys():
            self.announce(log.error, self.msg_duplicate_task_name, name=task.name)
            raise DuplicateTaskException(task.name)
        task.attach_manager(self)
        self.tasks[task.name] = task

    def get_last_added_task(self):
        """Get the task that was last added to this TaskManager"""
        if not self.tasks.keys():
            raise ValueError('No tasks yet')
        last_task_key = self.tasks.keys()[-1]
        return self.tasks[last_task_key]

    @utils.run_async
    def go_no_wait(self):
        """trigger the TaskManager without waiting for its completion, not the normal way of running a TaskManager"""
        self.go()

    def wait(self, timeout=None, **kwargs):
        """
        wait for the taskmanager to finish,
        if timeout is given and reached - waiting will stop but taskmanager will not
        """
        return utils.wait_for_callback_value(lambda: self.finished, True, timeout=timeout, **kwargs)

    def go(self):
        """Trigger the TaskManager, this is the main way to start a TaskManager"""
        self._prepare()
        self._start()
        try:
            self._operating_loop()
        finally:
            self._finish()

    def _prepare(self):
        """triggered when we want to start operating, before we actually start anything"""
        pass

    def _start(self):
        """triggered when operating loop begins"""
        self._announce_starting()
        self.start_time = time.time()
        self.operating = True

    def _announce_starting(self):
        """announce the TaskManager is starting"""
        self.announce(log.info, self.msg_starting, tasks=len(self.tasks))

    def _finish(self):
        """triggered when operating loop finished"""
        self.end_time = time.time()
        self.operating = False
        self.finished = True
        self._announce_finishing()

    def _announce_finishing(self):
        """announce the TaskManager is finishing"""
        self.announce(log.info, self.msg_finishing, time=int(self.duration))

    def _operating_loop(self):
        """main operating loop"""
        while self.operating:
            # check all finished
            if self.all_tasks_finished:
                break
            # check the conditions
            self._operating_check_conditions()
            # check if there is a problem and we should stop
            if self._operating_check_stop():
                break
            # start new tasks
            self._operating_start_new_tasks()
            # give some time before iterations
            time.sleep(1)
        else:
            self.handle_operating_loop_halted()

    def _operating_check_conditions(self):
        """check all conditions during operating"""
        self.check_running_tasks_for_timeout()

    def _operating_check_stop(self):
        """check if we need to stop operating for any reason"""
        return bool(self.stop_operating)

    def _operating_start_new_tasks(self):
        """while operating we should start new tasks when they are ready"""
        for task_name in sorted(self._get_ready_tasks()):
            self.handle_start_new_task(task_name)

    def handle_start_new_task(self, task_name):
        """
        how we start new tasks
        :param task_name:
        :return:
        """
        task = self.tasks[task_name]
        task.go(self.dry_run)

    def check_running_tasks_for_timeout(self):
        """checks all running tasks for timeouts"""
        for task_name, task in self._iter_running_tasks():
            if task.check_timeout():
                self.handle_task_timeout(task)

    def handle_task_timeout(self, task):
        """handle a task reaching its timeout"""
        self.announce(log.error, self.msg_task_timeout,
                      task=task.name, timeout=task.timeout, elapsed=int(task.elapsed_time))
        task.kill_task()
        self.stop_operating = True

    def handle_task_reports_finished(self, task):
        """when a task is finished it will call this method"""
        if self.report_still_running_tasks:
            currently_running_tasks = self._get_running_tasks()
            if currently_running_tasks:
                self.announce(log.debug, self.msg_tasks_still_running, still_running=currently_running_tasks)

    def handle_operating_loop_halted(self):
        """what happens when operating=False during the main loop"""
        self.announce(log.error, self.msg_operating_halted, current_tasks=self._get_running_tasks())
        if self.stop_running_tasks_on_halt:
            self.stop_all_tasks()

    def stop_all_tasks(self):
        """stop all tasks that are currently running"""
        for task_name, task in self._iter_running_tasks():
            task.kill_task()

    def _get_ready_tasks(self):
        """gets all the task names of all tasks that are ready to operate"""
        return [task_name for task_name, task in self._iter_ready_tasks()]

    def _get_running_tasks(self):
        """gets all the task names of all tasks that are currently operating"""
        return [task_name for task_name, task in self._iter_running_tasks()]

    def _get_finished_tasks(self):
        """gets all the task names of all tasks that are finished"""
        return [task_name for task_name, task in self._iter_finished_tasks()]

    def _iter_tasks(self):
        """yields all tasks in the task dict"""
        for task_name, task in self.tasks.items():
            yield task_name, task

    def _iter_finished_tasks(self):
        """yields all the tasks which are finished"""
        for task_name, task in self._iter_tasks():
            if not task.finished:
                continue
            yield task_name, task

    def _iter_running_tasks(self):
        """yields all the tasks which are currently operating"""
        for task_name, task in self._iter_tasks():
            if not task.operating:
                continue
            yield task_name, task

    def _iter_ready_tasks(self):
        """yields all the tasks which are ready to operate"""
        for task_name, task in self._iter_tasks():
            # we will iterate all the tasks,
            # and each task which we can detect is not ready we will skip (continue)
            # that way only the tasks that are ready now will be yielded
            if task.operating:
                continue  # it's already running
            if task.finished:
                continue  # it's already finished
            # since we did not skip (continue) then this task must be ready
            yield task_name, task

    @property
    def all_tasks_finished(self):
        """checks if all tasks are finished"""
        return all(task.finished for task in self.tasks.values())

    @property
    def duration(self):
        """gets the current duration of the TaskManager since it started, or the final duration if its finished"""
        if not self.start_time:
            return None
        if not self.end_time:
            duration = time.time() - self.start_time
            self.announce(log.trace, self.msg_duration_in_progress, duration=int(duration))
            return duration
        return self.end_time - self.start_time


class RCTaskManager(AbstractTaskManager):

    default_continue_rcs = (0, 1)
    msg_task_fail_rc = 'TaskManager stopping, Task got fail rc'

    def __init__(self, name, **kwargs):
        # optional parameters
        self.continue_rcs = kwargs.pop('continue_rcs', self.default_continue_rcs)

        # call super
        super(RCTaskManager, self).__init__(name, **kwargs)

    def _operating_check_conditions(self):
        """check all conditions during operating"""
        super(RCTaskManager, self)._operating_check_conditions()
        self.check_finished_tasks_for_fail_rc()

    def check_finished_tasks_for_fail_rc(self):
        """check all running tasks for fail rc"""
        for task_name, task in self._iter_finished_tasks():
            if task.rc not in self.continue_rcs:
                self.handle_task_fail_rc(task)

    def handle_task_fail_rc(self, task):
        """handles a task that gets a fail rc"""
        self.announce(log.error, self.msg_task_fail_rc, task=task.name, rc=task.rc)
        self.stop_operating = True

    @property
    def worst_rc(self):
        """returns the worst rc from all the tasks"""
        # first lets find if any rc is above 0, if so then we can return it
        rc = max(self.task_rcs.values())
        if rc > 0:
            return rc
        # if no rc is above 0 we need to check for negative rc, if so then we return it
        rc = min(self.task_rcs.values())
        if rc < 0:
            return rc
        # if no rc is above or below 0 then that means that the rc is 0 and everything is okay!
        return 0

    @property
    def task_rcs(self):
        """returns a dictionary of all task names and their rc"""
        return {task_name: task.rc for task_name, task in self._iter_tasks()}


class OrderedTaskManager(RCTaskManager):

    msg_missing_reference = 'TaskManager missing task references'

    def __init__(self, name, **kwargs):
        # optional parameters
        self.auto_reqs_from_previous_task = kwargs.pop('auto_reqs_from_previous_task', False)

        # call super
        super(OrderedTaskManager, self).__init__(name, **kwargs)

    @property
    def active_tasks(self):
        return {task_name: task for task_name, task in self.tasks.items() if task.active}

    @property
    def last_added_task(self):
        """Get the task that was last added to this TaskManager"""
        if not self.tasks.keys():
            raise ValueError('No tasks yet')
        last_task_key = self.tasks.keys()[-1]
        return self.tasks[last_task_key]

    def add_task(self, task):
        """
        how we populate the TaskManager with Tasks
        :param task:
        :return:
        """
        # assert hasattr(task, 'reqs') and isinstance(task.reqs, set)
        if self.auto_reqs_from_previous_task and self.tasks.keys() and not task.reqs:
            # override with a new set() that has only the last added task
            task.reqs = {self.last_added_task.name}
        return super(OrderedTaskManager, self).add_task(task)

    def _prepare(self):
        """
        how we prepare for execution
        :return:
        """
        super(OrderedTaskManager, self)._prepare()
        self.verify_task_workflow()
        self.remove_deactivated_tasks()

    def _announce_starting(self):
        """announce the TaskManager is starting"""
        self.announce(log.info, self.msg_starting, active_tasks=len(self.active_tasks))

    def _announce_finishing(self):
        """announce the TaskManager is finishing"""
        self.announce(log.info, self.msg_finishing, time=int(self.duration), worst_rc=self.worst_rc)

    def go(self):
        """Trigger the TaskManager, this is the main way to start a TaskManager"""
        super(OrderedTaskManager, self).go()
        return self.worst_rc

    def _iter_tasks(self):
        """yields all active tasks in the task dict"""
        for task_name, task in super(OrderedTaskManager, self)._iter_tasks():
            if not task.active:
                continue  # it's deactivated (skip)
            yield task_name, task

    def _iter_ready_tasks(self):
        """yields all the tasks which are ready to operate"""
        for task_name, task in super(OrderedTaskManager, self)._iter_ready_tasks():
            # we will iterate all the tasks,
            # and each task which we can detect is not ready we will skip (continue)
            # that way only the tasks that are ready now will be yielded
            if not all(self.tasks[t].finished for t in task.reqs):
                continue  # requirements are not finished
            # since we did not skip (continue) then this task must be ready
            yield task_name, task

    def remove_deactivated_tasks(self):
        """
        one of the task workflow population functions.
        removes all deactivated tasks from the workflow by marking them as finished
        and adjusting the required tasks of the next tasks (removing the deactivated task)
        and adjusting the next tasks of the required tasks (removing the deactivated task)
        """
        deactivated_tasks = [task for task in self.tasks.values() if not task.active]
        for deactivated_task in deactivated_tasks:
            deactivated_task.finished = True  # protection from issues
            self._remove_task_and_adjust_neighbors(deactivated_task)

    def _remove_task_and_adjust_neighbors(self, task):
        """
        one of the task workflow population functions.
        removes a deactivated tasks from the workflow. usually called internally by "remove_deactivated_tasks"
        adjusting the required tasks of the next tasks (removing the deactivated task)
        adjusting the next tasks of the required tasks (removing the deactivated task)
        """
        # adjust task requirements for flow logic
        for nt in (self.tasks[t] for t in task.next_tasks):
            nt.reqs.update(task.reqs)
            if task.name in nt.reqs:
                nt.reqs.remove(task.name)

        # adjust next tasks for debugging and logging
        for rt in (self.tasks[t] for t in task.reqs):
            rt.next_tasks.update(task.next_tasks)
            if task.name in rt.next_tasks:
                rt.next_tasks.remove(task.name)

    def verify_task_workflow(self):
        """
        one of the task workflow population functions.
        verifies that all task references exist
        :return:
        """
        for task in self.tasks.values():
            missing_task_references = [tr for tr in task.reqs if tr not in self.tasks.keys()]
            if missing_task_references:
                self.announce(log.error, self.msg_missing_reference, task=task.name, missing=missing_task_references)
                raise MissingTaskReferenceException(task, missing_task_references)


class Task(OrderedTask):
    pass


class SubManagerTask(Task):

    def __init__(self, name, manager, fargs=None, fkwargs=None, **kwargs):
        assert isinstance(manager, SubTaskManager)
        self.sub_task_manager = manager
        super(SubManagerTask, self).__init__(name, self.start, fargs, fkwargs, **kwargs)

    def start(self, *args, **kwargs):
        return self.sub_task_manager.go()

    def attach_manager(self, task_manager):
        super(SubManagerTask, self).attach_manager(task_manager)
        self.sub_task_manager.attach_manager(task_manager)


class TaskManager(OrderedTaskManager):
    pass


class SubTaskManager(TaskManager):

    msg_parent_manager_stopped = 'Parent TaskManager no longer operating'

    def __init__(self, name, **kwargs):
        self.parent_task_manager = None
        super(SubTaskManager, self).__init__(name, **kwargs)

    def attach_manager(self, task_manager):
        self.parent_task_manager = task_manager

    def _operating_check_conditions(self):
        """check all conditions during operating"""
        super(SubTaskManager, self)._operating_check_conditions()
        self.check_parent_manager_still_operating()

    def check_parent_manager_still_operating(self):
        """check the parent manager is still operating, if not we need to stop too"""
        if self.parent_task_manager and not self.parent_task_manager.operating:
            self.handle_parent_manager_not_operating()

    def handle_parent_manager_not_operating(self):
        """handles a task that gets a fail rc"""
        self.announce(log.error, self.msg_task_fail_rc)
        self.stop_operating = True

    @property
    def log_display(self):
        """
        How we should display this SubTaskManager in the log messages (announcements)
        :return:
        """
        return "SubTaskManager(name='{}' parent='{}')".format(
            self.name, self.parent_task_manager.name if self.parent_task_manager else '')


# CONVENIENCE task list and taskmanager generators


def simple_task_list_gen(*funcs, **kwargs):
    """generate a list of tasks from a list of functions with no arguments or requirements"""
    indexed = kwargs.pop('indexed', False)
    tasks = []
    for idx, func in enumerate(funcs, start=1):
        func_name = utils.sanitize(utils.get_func_name(func))
        if indexed:
            func_name = '{}_{}'.format(idx, func_name)
        t = Task(name=func_name, func=func)
        tasks.append(t)
    return tasks


def create_flat_manager(name, *tasks, **kwargs):
    """tasks have no requirements and all run at the same time"""
    tm = TaskManager(name=name, **kwargs)
    for task in tasks:
        if task.reqs:
            raise TaskException('task has requirements', task)
        tm.add_task(task)
    return tm


def create_serialized_manager(name, *tasks, **kwargs):
    """tasks have no requirements and run one at a time in order given"""
    kwargs.setdefault('auto_reqs_from_previous_task', True)
    tm = TaskManager(name=name, **kwargs)
    for task in tasks:
        if task.reqs:
            raise TaskException('task has requirements', task)
        tm.add_task(task)
    return tm


# CONVENIENCE ret validators // common validations

def validate_not_none(ret):
    return 0 if ret is not None else 2


def validate_path_exists(ret):
    return 0 if os.path.exists(ret) else 2


def validate_truthy(ret):
    return 0 if bool(ret) else 2


def validate_is_true(ret):
    return 0 if ret is True else 2
