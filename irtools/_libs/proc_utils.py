#! /usr/bin/env python

# Standard Imports
import time
import subprocess
from collections import namedtuple
from functools import partial
from wait_utils import wait_for_callback_value

# Lib Imports
from exec_utils import iexec
from file_utils import write_file
from csv_utils import DictReader

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.proc')

# process detailed information
ProcDetailedInfo = namedtuple('ProcDetailedInfo', 'pid name ppid status cmdline')

# todo: consolidate process operations that do similar thing - perhaps make a class that wraps the whole thing


def get_processes(name, log_id=None, **kwargs):
    kwargs.setdefault('to_console', False)
    kwargs.setdefault('show_log', False)
    kwargs.setdefault('trace_file', ir_artifact_dir + '/get_processes.trace.out')
    if running_on_windows:
        if kwargs.pop('partial', False):
            name += '*'
        collect_ret = iexec('tasklist /FI "IMAGENAME eq {}" /FO CSV'.format(name), **kwargs)
        procs = [row['Image Name'] for row in DictReader(collect_ret.out)]
    else:
        collect_ret = iexec('pgrep {} -l'.format(name), **kwargs)
        procs = [line.split()[-1] for line in collect_ret.out if line]
    write_file(ir_artifact_dir + '/get_procs.out', collect_ret.append_output(log_id), mode='a')
    return procs


def get_proc_list(proc_list, **kwargs):
    """
    given a list of procs, will return all the procs that are running
    :param proc_list: a list of strings (proc names)
    :param kwargs:
    :return:
    """
    import psutil
    # kwargs
    get_partial = kwargs.pop('partial', True)
    ignore_case = kwargs.pop('ignore_case', True)
    allow_empty_list = kwargs.pop('allow_empty_list', False)
    if isinstance(proc_list, str):
        proc_list = [proc_list]
    # members
    procs = []
    # loop procs
    if not proc_list and not allow_empty_list:
        raise RuntimeError('no proc_list supplied to get_proc_list')
    else:
        names = {name.lower() if ignore_case else name: name for name in proc_list}
        for proc in psutil.process_iter():
            try:
                proc_name = proc.name().lower() if ignore_case else proc.name()
                for name in names.keys():
                    if (get_partial and ((name in proc_name) or (proc_name in name))) or name == proc_name:
                        procs.append(names.pop(name))
                        break
            except psutil.AccessDenied:
                continue
            except psutil.NoSuchProcess as exc:
                log.trace('Exception during process iteration: exc={}'.format(exc))
    # return results
    return procs


def get_proc_pids_by_cmd(cmd_part, **kwargs):
    """
    uses psutils to get list of all proc pids with cmd_part in their commands
    :param cmd_part:
    :param kwargs:
    :return:
    """
    trace_file = kwargs.pop('trace_file', ir_artifact_dir + '/procs_by_cmd.txt')
    search_in_string = kwargs.pop('search_in_string', True)
    my_children_only = kwargs.pop('my_children_only', False)
    import psutil

    procs, content = [], ['cmd_part={}'.format(cmd_part)]

    if my_children_only:
        iterator = psutil.Process().children(recursive=True)
    else:
        iterator = psutil.process_iter()

    for proc in iterator:
        try:
            proc_parts = proc.cmdline()
            proc_string = subprocess.list2cmdline(proc_parts)
            if search_in_string:
                if cmd_part not in proc_string:
                    continue
            else:
                if cmd_part not in proc_parts:
                    continue
            procs.append(proc.pid)
            content.append(proc_string)
        except psutil.AccessDenied:
            continue
        except psutil.NoSuchProcess as exc:
            log.trace('Exception during process iteration: exc={}'.format(exc))

    if trace_file:
        content.append('---')
        write_file(trace_file, content, mode='a')

    return procs


def get_proc_pids(name, partial=False, **kwargs):
    """
    get proc pids (returns a list of matching pids) if only one proc matches, list will only have 1 item.
    returns a list for consistency. uses psutil
    :param name: proc name (or partial)
    :param partial: specify if partial name
    :param kwargs:
    :return: list of pids
    """
    import psutil

    # params
    ignore_case = kwargs.get('ignore_case', True)

    # members
    pids = []
    if ignore_case:
        name = name.lower()

    # check procs
    for proc in psutil.process_iter():
        try:
            proc_name = proc.name().lower() if ignore_case else proc.name()
            if (partial and name in proc_name) or name == proc_name:
                pids.append(proc.pid)
        except psutil.AccessDenied:
            continue

    return pids


def get_proc_name_from_pid(pid):
    """
    using psutil to obtain proc name from pid
    :param pid:
    :return: proc name
    """
    import psutil

    return psutil.Process(pid).name()


def wait_for_process_done_by_name(*procs, **kwargs):
    """
    Wait for all processes in list to not be running (done or killed)
    :param procs:
    :param kwargs:
    :return:
    """
    period = kwargs.pop('period', 2)
    timeout = kwargs.pop('timeout', 360)

    kwargs.setdefault('partial', True)

    log.debug('waiting for procs to be finished: procs={} timeout={}'.format(procs, timeout))

    def callback():
        procs_running = get_proc_list(procs, **kwargs)
        return len(procs_running)

    return wait_for_callback_value(
        callback, 0, timeout=timeout, period=period, return_callback_result=True, identification='wait_for_process'
    )


def detailed_proc_info_from_pids(pids):
    """
    using psutil to obtain proc details from a pids list
    :param pids: a list of pids
    :return: a list of ProcDetailedInfo namedtuple elements of all given pids
    """
    return [detailed_proc_info_pid(pid) for pid in pids]


def detailed_proc_info_pid(pid):
    """
    using psutil to obtain proc details from a pids list
    :param pid: pid
    :return: ProcDetailedInfo
    """
    import psutil

    try:
        proc = psutil.Process(pid)
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        return ProcDetailedInfo(pid, None, None, None, None)
    else:
        return ProcDetailedInfo(proc.pid, proc.name(), proc.ppid(), proc.status(), proc.cmdline())


def kill_child_procs(**kwargs):
    """Uses kill_process on child prcs, convenience function"""
    kwargs['myself'] = True
    kwargs['children_only'] = True
    success = kill_process(**kwargs)
    return 0 if success else 1


def kill_process(kill_all=False, pid=None, name=None, cmd_part=None, mode='psutil', children_only=False, myself=False,
                 partial=False, signum='9', safe_kill=None, wait_time_after_kill=60, **kwargs):
    """
    Kills a process by PID, Name, or Partial name.
    Can kill first matched process or all matched processes
    :param myself:
    :param children_only:
    :param wait_time_after_kill:
    :param safe_kill:
    :param signum:
    :param partial:
    :param pid: PID of the process to kill
    :param name: Name of the process to kill
    :param cmd_part: Partial command used to run the process to kill (cmd_part only works with psutil mode)
    :param kill_all: Specify as True to kill all processes, otherwise just first
    :param mode: Specify psutil or cmdline
    :return: True if process(s) were killed, False otherwise.
    """
    # kwargs
    pkn = int(signum)  # pkill num (signum)
    assert pkn in [9, 15]

    if myself:
        if pid:
            log.warn('killing process with "myself" flag overrides pid')
        pid = os.getpid()

    if children_only:
        if mode == 'cmdline':
            log.warn('killing process with "children only" flag overrides mode')
        mode = 'psutil'

    # verify params
    if not any([pid, name, cmd_part]):
        raise ValueError('Must supply at least one of [pid, name, cmd_part] as kwargs.')
    # make a param object for logs?
    sid = ' '.join(['{}={}'.format(k, v) for k, v in {'pid': pid, 'name': name, 'cmd_part': cmd_part}.items() if v])

    if mode not in ['psutil', 'cmdline']:
        log.warn('kill_process, invalid mode, (ignoring, using default): mode={}'.format(mode))
        mode = 'psutil'

    # return value
    proc_was_killed = False

    if mode == 'psutil':
        # todo: simplify this horrible code
        try:
            import psutil
        except ImportError:
            psutil = None
            log.warn('Could not import psutil for kill_process, trying cmdline')
            mode = 'cmdline'
        else:
            log.trace('Iterating processes with psutil: kwrgs={}'.format(kwargs))
            for proc in psutil.process_iter():
                try:
                    log.trace('examining process: pid={} name={} cmd_part={}'.format(
                        int(proc.pid), proc.name(), proc.cmdline()))
                    if ((pid and int(proc.pid) == int(pid)) or
                            (name and proc.name() == name) or
                            (cmd_part and cmd_part in subprocess.list2cmdline(proc.cmdline())) or
                            (partial and name and name.lower() in proc.name().lower())):
                        if safe_kill is not None and not safe_kill(proc.pid):
                            continue
                        try:
                            log.trace('getting children of process: proc={}'.format(proc))
                            childrens = proc.children(recursive=True)
                            log.trace(
                                'Killing procs: pid={} name={} ppid={} status={} cmdline={} children_only={} '
                                'childrens={}'.format(proc.pid, proc.name, proc.ppid, proc.status, proc.cmdline,
                                                      children_only, childrens))
                            for child in childrens:
                                log.trace('examining child: child={} pid={} name={} cmd_part={}'.format(
                                    child, int(proc.pid), proc.name(), proc.cmdline()))
                                if pkn == 9:
                                    child.kill()
                                else:
                                    child.terminate()
                            if not children_only:
                                if pkn == 9:
                                    proc.kill()
                                else:
                                    proc.terminate()
                        except psutil.NoSuchProcess as nsp:
                            log.trace('no such process error-in: msg={} kwargs={}'.format(nsp.msg, kwargs))
                        try:
                            if not children_only:
                                proc.wait(wait_time_after_kill)
                        except psutil.TimeoutExpired as te:
                            log.error('timeout waiting for proc to be killed: sid={} exc={}'.format(sid, te))
                            raise
                        else:
                            proc_was_killed = True
                        if not kill_all:
                            break
                except psutil.AccessDenied:
                    continue
                except psutil.NoSuchProcess as nsp:
                    log.trace('no such process error-out: msg={} kwargs={}'.format(nsp.msg, kwargs))
                    continue

        # process was not killed
        if not proc_was_killed:
            if name or pid:
                # fallback to cmdline (name or pid are mandatory for this mode)
                log.warn('failed to kill proc with psutil, falling back to cmdline: {}'.format(sid))
                mode = 'cmdline'
            else:
                log.error('failed to kill proc with psutil: {}'.format(sid))

    if mode == 'cmdline':
        if name:
            if partial:
                name += '*'
            cmd = 'taskkill /IM "{}" /F /T'.format(name) if running_on_windows else 'pkill -{} "{}"'.format(pkn, name)
        elif pid and ((safe_kill is None) or safe_kill(pid)):
            cmd = 'taskkill /PID "{}" /F /T'.format(pid) if running_on_windows else 'kill -{} "{}"'.format(pkn, pid)
        else:
            raise RuntimeError('This is impossible!')

        ret = iexec(cmd)
        if ret.rc == 0 or ret.rc == 1 and ret.contains('No such process'):
            proc_was_killed = True
        write_file(ir_artifact_dir + '/kill_proc.out', mode='a',
                   contents='KWARGS={}\nRET={}\n\n'.format(kwargs, ret))

    return proc_was_killed


__all__ = [
    'kill_process', 'kill_child_procs',
    'get_processes', 'get_proc_list', 'get_proc_name_from_pid', 'get_proc_pids', 'get_proc_pids_by_cmd',
    'wait_for_process_done_by_name',
    'detailed_proc_info_from_pids', 'detailed_proc_info_pid'
]
