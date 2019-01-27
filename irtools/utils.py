#! /usr/bin/env python

# Standard Imports
from optparse import OptionParser
import collections
import signal

# Library Imports
from __init__ import *
from _libs.csv_utils import *
from _libs.decorator_utils import *
from _libs.mail_utils import *
from _libs.byte_utils import *
from _libs.file_utils import *
from _libs.exec_utils import *
from _libs.log_utils import *
from _libs.package_utils import *
from _libs.proc_utils import *
from _libs.service_utils import *
from _libs.string_utils import *
from _libs.ssh_utils import *
from _libs.enum_utils import *
from _libs.report_utils import *
from _libs.env_utils import *
from _libs.sort_utils import *
from _libs.docker_utils import *
from _libs.datetime_utils import *
from _libs.linux_utils import *
from _libs.wait_utils import *
from _libs.func_utils import *

# logging
log = logging.getLogger('irtools.utils')


# Classes
class OrderedSet(collections.MutableSet):
    # from: https://code.activestate.com/recipes/576694/

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, _next = self.map.pop(key)
            prev[2] = _next
            _next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)


class AttributeDict(dict):
    """
    allows the dictionary to be accessed by dic.attribute.
    dic[key] == dic.key; both for get and set.
    """
    def __getattr__(self, attr):
        return self[attr] if attr in self.keys() else None

    def __setattr__(self, attr, value):
        self[attr] = value


def gen_dict(**kwargs):
    return AttributeDict(kwargs)


class SignalCatcher:
    """
    Catch signals to allow graceful shutdown.
    @ https://github.com/ryran/reboot-guard/blob/master/rguard#L284:L304
    """
    def __init__(self, signals=None):
        self.last_signal = None
        self.received_signal = False
        self.received_term_signal = False
        # signals
        signals = signals or [1, 2, 3, 10, 12, 15]
        self.originals = {signum: signal.getsignal(signum) for signum in signals}
        for signum in signals:
            signal.signal(signum, self.handler)

    def set_handler(self, signum, handler):
        signal.signal(signum, handler)

    def handler(self, signum, frame):
        log.warn('got signal: signum={}'.format(signum))

        # signal.signal(signum, self.originals[signum])

        self.last_signal = signum
        self.received_signal = True
        if signum in [2, 3, 15]:
            self.received_term_signal = True

        signal.signal(signum, self.handler)


# Functions
def noop(*args, **kwargs):
    """
    No Operation Func - Does Nothing!
    :param args:
    :param kwargs:
    :return:
    """
    pass


def try_get_rc(ret, raise_on_fail=False, fail_rc=3, **kwargs):
    """
    try to get a numeric RC
    :param ret: the object to examine for an rc
    :param raise_on_fail:
    :param fail_rc:
    :return:
    """

    rc_attributes = kwargs.pop('rc_attributes', ['rc'])
    parse_execresults = kwargs.pop('parse_execresults', True)

    # first, if it is an int, return it
    if isinstance(ret, int):
        return int(ret)

    # if it is an ExecResult, return the RC
    if parse_execresults and isinstance(ret, ExecResult):
        return ret.rc

    # if it has an rc attribute, return that (if its an in)
    if isinstance(rc_attributes, (list, tuple, set)):
        for rc_attribute in rc_attributes:
            if hasattr(rc_attribute, ret):
                r = getattr(ret, rc_attribute)
                if isinstance(r, int):
                    return int(r)

    # if i should raise on fail, raise now
    if raise_on_fail:
        raise RuntimeError('no rc for object: ret={}'.format(repr(ret)))

    return fail_rc  # exception ?


def deepgetattr(obj, attr, default=None, raise_if_missing=False):
    """Recurses through an attribute chain to get the ultimate value."""
    if isinstance(attr, str):
        attr = attr.split('.')
    try:
        return reduce(getattr, attr, obj)
    except AttributeError:
        if raise_if_missing:
            raise
        return default


def deepgetkey(col, key, default=None, raise_if_missing=False):
    """Recurses through a key chain to get the ultimate value."""
    if isinstance(key, str):
        key = key.split('.')
    try:
        return reduce(dict.get, key, col)
    except KeyError:
        if raise_if_missing:
            raise
        return default


def is_same_class_or_subclass(target, main_class):
    """
    checks if target is the same class or a subclass of main_class
    :param target:
    :param main_class:
    :return:
    """
    return isinstance(target, main_class) or issubclass(target.__class__, main_class)


def is_bool_or_none(value):
    return any(value is t for t in (None, True, False))


def parse_cmdline_args(fargs, fkwargs, args):
    fargs = fargs[:]
    fkwargs = convert_list_of_string_params_to_dict(fkwargs, as_bools=True)
    for arg in args:
        if arg.count('=') == 1:
            key, value = arg.partition('=')
            fkwargs[key] = bool_from_text(value)
        else:
            fargs.append(arg)
    return fargs, fkwargs


def main(args):
    parser = OptionParser()
    parser.add_option('--log-level', '--ll', dest='log_level', help='Log Level (0=info, 1=debug, 2=trace)')
    parser.add_option('--log-file', '--lf', dest='log_file', help='Log file', default=ir_log_dir + '/utils.log')
    parser.add_option('-a', '--arg', dest='fargs', action='append', default=[])
    parser.add_option('-k', '--kwarg', dest='fkwargs', action='append', default=[])
    options, args = parser.parse_args(args)

    logging_setup(log_level=options.log_level, log_file=options.log_file)

    if not args:
        parser.error('No function specified')
        return 0

    functions = {key: value for key, value in globals().items() if callable(value)}
    func_name = args[0]
    func = functions.get(func_name)

    if not func or not callable(func):
        parser.error('Function does not exist: {}'.format(func_name))
        return 1

    fargs, fkwargs = parse_cmdline_args(options.fargs, options.fkwargs, args[1:])

    try:
        ret = func(*fargs, **fkwargs)
    except Exception as exc:
        log.error('Exception when executing function: func={} exc={}'.format(func_name, exc))
        raise
    if isinstance(ret, ExecResult):
        log.debug('utils results: fun={} rc={}'.format(func_name, ret.rc))
        return ret.rc
    return ret


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
