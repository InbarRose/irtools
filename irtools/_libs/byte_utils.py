#! /usr/bin/env python

# Standard Imports
from collections import namedtuple

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.byte')

# Disk Stuff
DiskUsage = namedtuple('DiskUsage', 'total used free')
SYMBOLS = {  # see: http://goo.gl/kTQMs
    'customary': ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    'customary_ext': ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa', 'zetta', 'iotta'),
    'iec': ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
    'iec_ext': ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi', 'zebi', 'yobi'),
}


def get_disk_usage(path=None, human_readable=False):
    """
    Return disk usage statistics for the given path as a (total, used, free) namedtuple (values are expressed in bytes)
    """
    # Author: Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
    # License: MIT
    # modified from: http://code.activestate.com/recipes/577972-disk-usage/
    path = path or os.path.abspath(os.sep)
    log.trace('getting disk usage: path={}'.format(path))

    if hasattr(os, 'statvfs'):  # POSIX
        st = os.statvfs(path)
        free = st.f_bavail * st.f_frsize
        total = st.f_blocks * st.f_frsize
        used = (st.f_blocks - st.f_bfree) * st.f_frsize
        du = DiskUsage(total, used, free)

    elif os.name == 'nt':  # Windows
        import ctypes
        _, total, free = ctypes.c_ulonglong(), ctypes.c_ulonglong(), ctypes.c_ulonglong()
        if sys.version_info >= (3,) or isinstance(path, unicode):
            fun = ctypes.windll.kernel32.GetDiskFreeSpaceExW
        else:
            fun = ctypes.windll.kernel32.GetDiskFreeSpaceExA
        ret = fun(path, ctypes.byref(_), ctypes.byref(total), ctypes.byref(free))
        if ret == 0:
            raise ctypes.WinError()
        used = total.value - free.value
        du = DiskUsage(total.value, used, free.value)

    else:
        raise NotImplementedError("platform not supported")

    if human_readable:
        return DiskUsage(bytes2human(du.total), bytes2human(du.used), bytes2human(du.free))
    return du


def check_file_size(file_path, min_file_size=0):
    """
    Check file size is greater than min_file_size. Default is larger than 0 bytes.
    :param file_path:
    :param min_file_size:
    :return:
    """
    try:
        size = os.path.getsize(file_path)
    except Exception as exc:
        log.error('Exception retrieving file size: file_path={} exc={}'.format(file_path, exc))
    else:
        log.trace('check file size: file={} min_file_size={} actual_size={}'.format(file_path, min_file_size, size))
        return bool(size > min_file_size)


def bytes2human(n, frmt='%(value).1f%(symbol)s', symbols='customary'):
    """
    Convert n bytes into a human readable string based on format.
    symbols can be either "customary", "customary_ext", "iec" or "iec_ext",
    see: http://goo.gl/kTQMs
    """
    # Bytes-to-human / human-to-bytes converter.
    # Based on: http://goo.gl/kTQMs
    # Working with Python 2.x and 3.x.
    #
    # Author: Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
    # License: MIT
    # copied from: http://code.activestate.com/recipes/578019-bytes-to-human-human-to-bytes-converter/?in=user-4178764
    n = int(n)
    if n < 0:
        raise ValueError("n < 0")
    symbols = SYMBOLS[symbols]
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i + 1) * 10
    for symbol in reversed(symbols[1:]):
        if n >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return frmt % locals()
    return frmt % dict(symbol=symbols[0], value=n)


def human2bytes(s):
    """
    Attempts to guess the string format based on default symbols
    set and return the corresponding bytes as an integer.
    When unable to recognize the format ValueError is raised.
    """
    # Bytes-to-human / human-to-bytes converter.
    # Based on: http://goo.gl/kTQMs
    # Working with Python 2.x and 3.x.
    #
    # Author: Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
    # License: MIT
    # copied from: http://code.activestate.com/recipes/578019-bytes-to-human-human-to-bytes-converter/?in=user-4178764
    init = s
    num = ""
    while s and s[0:1].isdigit() or s[0:1] == '.':
        num += s[0]
        s = s[1:]
    num = float(num)
    letter = s.strip()
    for name, sset in SYMBOLS.items():
        if letter in sset:
            break
    else:
        if letter == 'k':  # treat 'k' as an alias for 'K' as per: http://goo.gl/kTQMs
            sset = SYMBOLS['customary']
            letter = letter.upper()
        else:
            raise ValueError("can't interpret %r" % init)
    prefix = {sset[0]: 1}
    for i, s in enumerate(sset[1:]):
        prefix[s] = 1 << (i + 1) * 10
    return int(num * prefix[letter])


__all__ = ['human2bytes', 'bytes2human', 'get_disk_usage', 'check_file_size']
