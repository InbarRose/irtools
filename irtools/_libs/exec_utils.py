#! /usr/bin/env python

# Standard Imports
import select
import subprocess
import time
import tempfile
import pickle
import itertools
import multiprocessing
from datetime import datetime

# Lib Imports
from file_utils import write_file, read_file, get_tmp_dir
from log_utils import get_log_func, log_datetime_format
from string_utils import get_datestring

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.exec')


# kwargs for subprocess (used by iexec)
SUBPROCESS_KWARGS = ['bufsize', 'executable', 'stdin', 'stdout', 'stderr',
                     'preexec_fn', 'close_fds', 'shell', 'cwd', 'env',
                     'universal_newlines', 'startupinfo', 'creationflags']


class MultiProcess:
    # todo: move to own util / document
    counter = itertools.count()

    def __init__(self, name, func, args, kwargs):
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.proc = None

    def wait_read_result(self):
        self.join()
        if not self.kwargs.get('pickle_result', False):
            return self.exitcode
        with open(self.kwargs['pickle_result'], 'rb') as f:
            return pickle.load(f)

    def go(self):
        self.start()
        self.join()
        return self.exitcode

    def start(self):
        self.proc = multiprocessing.Process(target=self.func, name=self.name, args=self.args, kwargs=self.kwargs)
        self.proc.start()

    def join(self, timeout=None):
        self.proc.join(timeout)

    def is_alive(self):
        return self.proc.is_alive()

    def kill(self):
        self.proc.terminate()

    def get_pid(self):
        return self.proc.ident

    def send_signal(self, signal):
        if self.get_pid():
            return os.kill(self.get_pid(), signal)

    @property
    def exitcode(self):
        return self.proc.exitcode


class ExecResult:
    """Result of an execution. Has STDOUT and STDERR and RC."""
    def __init__(self, out=None, err=None, rc=0, time_taken=None, cmd=None, ordered_out=None, start=None, timeout=0):
        self.out = out or []
        self.err = err or []
        self.rc = rc
        self.__out = ''
        self.__err = ''
        self.time = time_taken
        self.start = start
        self.start_datetime = datetime.fromtimestamp(start).strftime(log_datetime_format)
        self.timeout = timeout
        self.cmd = cmd
        self.ordered_out = ordered_out

    def contents(self):
        """Returns all the content of the execution as a string, ordered if possible, else stdout first then stderr"""
        if self.ordered_out:
            return ''.join(self.ordered_out)
        return '\n'.join([self.out_string, self.err_string])

    def list_contents(self):
        """Returns all the content of the execution as a list, ordered if possible, else stdout first then stderr"""
        if self.ordered_out:
            return self.ordered_out
        return self.out + self.err

    def out_contains(self, content):
        """Check if stdout contains the content
        :param content:
        """
        return self._contains(content, self.out_string)

    def err_contains(self, content):
        """Check if stderr contains the content
        :param content:
        """
        return self._contains(content, self.err_string)

    def contains(self, content, collection_func=all):
        """Check if either stdout or stderr contains the content
        :param content: string or collection of strings
        :param collection_func: specify any or all func
        """
        if isinstance(content, str):
            return bool(self.out_contains(content) or self.err_contains(content))
        else:
            return collection_func(self.contains(c, collection_func) for c in content)

    @staticmethod
    def _contains(content, collection):
        """helper"""
        if isinstance(content, str):
            return bool(content in collection)
        elif isinstance(content, list):
            return all(c in collection for c in content)
        else:
            raise ValueError('Unsupported type: type={}'.format(type(content)))

    def debug_output(self):
        """returns a debug output string that is ready for printing or writing"""
        return '{head}\n\n{tail}'.format(head=self.get_dump_header(), tail=self.contents())

    def get_dump_header(self):
        """Formats all headers for dumping; cmd, rc, start, time"""
        headers = ['cmd', 'rc', 'start', 'start_datetime', 'time']
        head = '\n'.join(['{}: {}'.format(h, getattr(self, h)) for h in headers])
        return head

    def to_dump_file(self, dump_file, dump_file_rotate=False):
        """Dump to dump file, handles all writing and rotating"""
        dump_file = write_file(dump_file, contents=self.get_dump_header() + '\n\n', rotate=dump_file_rotate)
        return write_file(dump_file, contents=self.list_contents(), mode='a')

    def append_output(self, log_id=None):
        """returns a string representation of the object with extra newlines to be appended to for logging
        :param log_id:
        """
        if log_id is not None:
            return '{}: {}\n\n'.format(log_id, self.__str__())
        return '{}\n\n'.format(self.__str__())

    @property
    def out_string(self):
        if not self.__out:
            self.__out = ''.join(self.out)
        return self.__out

    @property
    def err_string(self):
        if not self.__err:
            self.__err = ''.join(self.err)
        return self.__err

    @property
    def bad_rc(self):
        return self.rc != 0

    @property
    def good_rc(self):
        return not self.bad_rc

    @property
    def bad(self):
        return self.bad_rc or self.err_string

    @property
    def good(self):
        return not self.bad

    def __repr__(self):
        return 'ExecResult(cmd={} out={} err={} rc={} start={} time={} timeout={})'.format(
            self.cmd, self.out, self.err, self.rc, self.start, self.time, self.timeout)

    def __str__(self):
        return str(self.__repr__())


def detached_iexec(cmd, **kwargs):
    """
    Multiprocess iexec, perform a command on local machine with a separate process.
    Immediately finishes, and you now hold a multi-process object that you can query and use to wait
    once complete you can access the ExecResult Object
    :param cmd: the command
    :param kwargs: any kwargs
    :return: MultiProcess Object to query until you get an ExecResult Object
    """
    entity = 'mpiexec.{}'.format(MultiProcess.counter.next())

    if kwargs.get('pickle_result', False):
        pickle_file = os.path.join(get_tmp_dir(use_logging=False), entity)
        kwargs['pickle_result'] = pickle_file

    mp = MultiProcess(entity, iexec, [cmd], kwargs)
    mp.start()
    return mp


def mpiexec(cmd, **kwargs):
    """
    Multiprocess iexec, perform a command on local machine with a separate process.
    :param cmd: the command
    :param kwargs: any kwargs
    :return: ExecResult Object
    """
    entity = 'mpiexec.{}'.format(MultiProcess.counter.next())
    pickle_file = os.path.join(get_tmp_dir(use_logging=False), entity)
    kwargs['pickle_result'] = pickle_file
    mp = MultiProcess(entity, iexec, [cmd], kwargs)
    mp.go()
    with open(pickle_file, 'rb') as f:
        return pickle.load(f)


def iexec(cmd, **kwargs):
    """
    Perform a command on local machine with subprocess.Popen
    contains many conveniences and logging capabilities
    returns an ExecResult object which also contains many conveniences
    :param cmd: the command
    :param kwargs: any kwargs
    :return: ExecResult Object
    """
    show_log = kwargs.pop('show_log', True)
    to_console = kwargs.pop('to_console', True)
    print_to_console = kwargs.pop('print_to_console', False)
    redirect_output = kwargs.pop('redirect_output', False)
    redirect_file_name = kwargs.pop('redirect_file_name', None)
    log_as_debug = kwargs.pop('log_as_debug', False)
    log_as_trace = kwargs.pop('log_as_trace', False)
    log_as_level = kwargs.pop('log_as_level', None)
    pickle_result = kwargs.pop('pickle_result', '')
    dump_file = kwargs.pop('dump_file', None)
    trace_file = kwargs.pop('trace_file', None)
    timeout = kwargs.pop('timeout', 0)
    dump_file_rotate = kwargs.pop('dump_file_rotate', False)
    alt_out = kwargs.pop('alt_out', None)
    alt_err = kwargs.pop('alt_err', alt_out)
    iexec_communicate = kwargs.pop('iexec_communicate', None)

    if not isinstance(cmd, str):
        cmd = subprocess.list2cmdline(cmd)

    if redirect_output and running_on_windows:
        if redirect_file_name is None:
            redirect_file = tempfile.NamedTemporaryFile(
                suffix=".txt",
                prefix="gstmp.{}.redirect.".format(get_datestring()),
                dir=ir_artifact_dir,
                delete=False
            )
            # closing the file, since we just need its name and it must be closed before using redirect the output
            redirect_file.close()
            redirect_file_name = redirect_file.name
        cmd += ' > {} 2>&1'.format(redirect_file_name)

    if print_to_console:
        print cmd

    if show_log:
        msg = 'exec: {}'.format(cmd)
        if log_as_level:
            get_log_func(log_as_level)(msg)
        elif log_as_trace:
            log.trace(msg)
        elif log_as_debug:
            log.debug(msg)
        else:
            log.info(msg)

    pkwargs = {'shell': True, 'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE}
    for arg in SUBPROCESS_KWARGS:
        if arg in kwargs and arg not in pkwargs:
            pkwargs[arg] = kwargs[arg]

    stdout = []
    stderr = []
    ordered_out = []
    start_time = time.time()

    proc = subprocess.Popen(args=cmd, **pkwargs)

    def _write_to_stdout(line):
        if to_console:
            sys.stdout.write(line)
        if print_to_console:
            print line
        if alt_out is not None and callable(alt_out):
            alt_out(contents=line)
        stdout.append(line)
        ordered_out.append(line)

    def _write_to_stderr(line):
        if to_console:
            sys.stderr.write(line)
        if print_to_console:
            print line
        if alt_err is not None and callable(alt_err):
            alt_err(contents=line)
        stderr.append(line)
        ordered_out.append(line)

    if running_on_windows:
        if iexec_communicate:
            proc.communicate()
            return
        rc = proc.wait()
        if redirect_output:
            stdout = read_file(redirect_file_name)
        else:
            stdout = proc.stdout.readlines()
        stderr = proc.stderr.readlines()
        if to_console:
            sys.stdout.writelines(stdout)
            sys.stderr.writelines(stderr)
    else:
        reads = [proc.stdout.fileno(), proc.stderr.fileno()]
        while True:
            ret = select.select(reads, [], [])

            for fd in ret[0]:
                if fd == proc.stdout.fileno():
                    read = proc.stdout.readline()
                    _write_to_stdout(read)
                if fd == proc.stderr.fileno():
                    read = proc.stderr.readline()
                    _write_to_stderr(read)

            rc = proc.poll()
            if rc is not None:
                # finished proc, read all the rest of the lines from the buffer
                outs = proc.stdout.readlines()
                for read in outs:
                    _write_to_stdout(read)
                errs = proc.stderr.readlines()
                for read in errs:
                    _write_to_stderr(read)
                break

            if timeout and time.time() - start_time > timeout:
                raise RuntimeError('Timeout executing cmd on linux')

    time_taken = time.time() - start_time
    result = ExecResult(stdout, stderr, rc, time_taken, cmd, ordered_out, start_time, timeout)

    if dump_file:
        result.to_dump_file(dump_file, dump_file_rotate)

    if trace_file:
        write_file(trace_file, contents=result.append_output(), mode='a')

    if pickle_result:
        with open(pickle_result, 'wb') as f:
            pickle.dump(result, f, protocol=1)

    return result


__all__ = [
    'iexec', 'mpiexec', 'detached_iexec', 'ExecResult'
]
