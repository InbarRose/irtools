#! /usr/bin/env python

# Standard Imports
import uuid
import re

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.env')


def get_ip():
    """Gets the IP of this machine (if it can)"""
    return socket.gethostbyname(socket.gethostname())


def get_mac():
    """uses uuid lib to get mac"""
    mac_int = uuid.getnode()
    mac_str = _mac_int_to_str(mac_int)
    return mac_str


def _mac_int_to_str(mac_int):
    mac_str = ':'.join(("%012X" % mac_int)[i:i + 2] for i in range(0, 12, 2))
    return mac_str


def get_macs():
    """uses code found in uuid lib to get all mac addresses"""
    if running_on_windows:
        # Get the hardware address on Windows by running ipconfig.exe
        macs = set()
        dirs = ['', r'c:\windows\system32', r'c:\winnt\system32']
        for directory in dirs:
            try:
                pipe = os.popen(os.path.join(directory, 'ipconfig') + ' /all')
            except IOError:
                continue
            with pipe:
                for line in pipe:
                    value = line.split(':')[-1].strip().lower()
                    if re.match('([0-9a-f][0-9a-f]-){5}[0-9a-f][0-9a-f]', value):
                        macs.add(int(value.replace('-', ''), 16))
        return map(_mac_int_to_str, macs)
    elif running_on_linux:
        # Get the hardware address on Unix by running ifconfig
        macs = set()

        def _find_macs(command, args, hw_identifiers, get_index):
            try:
                pipe = uuid._popen(command, args)
                if not pipe:
                    return
                with pipe:
                    for line in pipe:
                        words = line.lower().rstrip().split()
                        for i in range(len(words)):
                            if words[i] in hw_identifiers:
                                try:
                                    word = words[get_index(i)]
                                    mac = int(word.replace(':', ''), 16)
                                    if mac:
                                        macs.add(mac)
                                except (ValueError, IndexError):
                                    # Virtual interfaces, such as those provided by
                                    # VPNs, do not have a colon-delimited MAC address
                                    # as expected, but a 16-byte HWAddr separated by
                                    # dashes. These should be ignored in favor of a
                                    # real MAC address
                                    pass
            except IOError:
                pass

        # This works on Linux ('' or '-a'), Tru64 ('-av'), but not all Unixes.
        for args in ('', '-a', '-av'):
            _find_macs('ifconfig', args, ['hwaddr', 'ether'], lambda i: i + 1)
        return map(_mac_int_to_str, macs)
    else:
        raise RuntimeError('unsupported platform')


def get_env(key, default=None, as_bool=False, as_int=False, clean=True):
    """
    Like os.getenv() but with some more functionality.
    :param key: The os env variable to retrieve
    :param default: The default return value (if is_bool and not default then default is '0')
    :param as_bool: Returns the value as a boolean, also casts the value as an integer first.
    :param as_int: Returns the value as an integer.
    :param clean:  Calls string.strip() on the returned value.
    :return: The Value of the env variable (or default), usually a string, unless as_bool is True.
    """
    # prepare defaults
    if as_bool:
        assert default in (None, True, False)
        default = False if default is None else default
    if as_int:
        assert isinstance(default, (int, type(None)))
        default = 0 if default is None else default
    # get value
    value = os.getenv(key, None)
    # clean
    if clean and value is not None and isinstance(value, str):
        value = value.strip()
    # convert
    if value is None:
        value = default
    elif as_bool:
        if not isinstance(value, bool):
            assert len(value) == 1 and value.isdigit()
            value = bool(int(value))
    elif as_int:
        assert value.isdigit()
        value = int(value)
    elif not isinstance(value, str):
        raise EnvironmentError('key value type invalid: key={} type={} value={}'.format(key, type(value), value))
    return value


__all__ = ['get_env', 'get_ip', 'get_mac', 'get_macs']
