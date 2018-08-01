#! /usr/bin/env python

# Standard Imports
import time
import shutil

# Lib Imports
from exec_utils import iexec

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.package')

# string patterns for apt / packages
locked_apt_get_file_msg = '/var/lib/dpkg/lock'
remove_dpkg_lock = 'sudo rm /var/lib/dpkg/lock; sudo dpkg --configure -a'
fix_dpkg_interruption = 'sudo dpkg --configure -a'
apt_get_fix_broken_packages = 'apt-get -f install'
pip_commands = ['python -m pip', 'pip']
if running_on_linux:
    pip_commands.append('sudo -H pip')


def apt_get_iexec(cmd, attempts=3, period=30, **kwargs):
    """Convenience function to retry failed/locked apt-get commands"""
    assert running_on_debian
    attempt = 0
    extra_exec_kwargs = {'to_console': False, 'log_as_trace': True, 'trace_file': kwargs.get('trace_file')}
    force_unlock = kwargs.pop('force_unlock', True)
    use_sudo = kwargs.pop('use_sudo', True)

    # base cmd
    if use_sudo:
        lock_cmd = 'sudo lsof /var/lib/dpkg/lock'
    else:
        lock_cmd = 'lsof /var/lib/dpkg/lock'
    # check if locked
    lock_check_ret = iexec(lock_cmd, **extra_exec_kwargs)
    if lock_check_ret.contains(locked_apt_get_file_msg) and force_unlock:
        iexec(remove_dpkg_lock, **extra_exec_kwargs)

    while True:
        attempt += 1
        ret = iexec(cmd, **kwargs)
        if attempt < attempts:
            if ret.contains(locked_apt_get_file_msg):
                log.warn('locked dpkg file, retrying')
            elif ret.contains(fix_dpkg_interruption):
                log.warn('fixing dpkg interruption, then retrying')
                iexec(fix_dpkg_interruption, **extra_exec_kwargs)
            elif ret.contains(apt_get_fix_broken_packages):
                log.warn('fixing broken packages, then retrying')
                base, _, _ = cmd.partition('apt-get')
                iexec(base + apt_get_fix_broken_packages + ' -y', **extra_exec_kwargs)
            else:
                break
            # keep going
            time.sleep(period)
            continue

        return ret
    return ret


def apt_get_install(*packages, **kwargs):
    """
    performs apt-get install on ubuntu with various optimizations to install a list of packages
    :param packages: package list
    :param kwargs: kwargs containing flags or iexec kwargs
    :return: ret
    """
    assert running_on_debian
    # kwargs
    clean = kwargs.pop('clean', True)
    update = kwargs.pop('update', True)
    non_interactive = kwargs.pop('non_interactive', True)
    use_sudo = kwargs.pop('use_sudo', True)

    kwargs.setdefault('trace_file', ir_artifact_dir + '/packages/apt/apt_get_trace.out')
    kwargs.setdefault('dump_file', ir_artifact_dir + '/packages/apt/apt_get_dump.out')
    kwargs.setdefault('dump_file_rotate', True)
    kwargs.setdefault('to_console', False)

    # flags
    flags = []
    if kwargs.pop('yes', True):
        flags.append('-y')
    if kwargs.pop('quiet', True):
        flags.append('-q')
    if kwargs.pop('fix_missing', True):
        flags.append('--fix-missing')

    # base cmd
    if use_sudo:
        base_cmd = 'sudo apt-get'
    else:
        base_cmd = 'apt-get'

    if non_interactive:
        base_cmd = 'DEBIAN_FRONTEND=noninteractive {}'.format(base_cmd)

    # clean
    if clean:
        apt_get_iexec('{} clean'.format(base_cmd), use_sudo=use_sudo, **kwargs)

    # update
    if update:
        apt_get_iexec('{} update'.format(base_cmd), use_sudo=use_sudo, **kwargs)

    # install
    log.debug('before installing: base_cmd={} flags={} packages={}'.format(base_cmd, flags, packages))
    cmd = '{} install {} {}'.format(base_cmd, ' '.join(flags), ' '.join(packages))
    return apt_get_iexec(cmd, use_sudo=use_sudo, **kwargs)


def yum_is_installed(package, **kwargs):
    """
    checks if a package is already installed using `rpm -q PACKAGE` and checking the return code.
    :param package: package name
    :param kwargs:
    :return:
    """
    assert running_on_centos
    # kwargs
    kwargs.setdefault('trace_file', ir_artifact_dir + '/packages/yum/yum_trace.out')
    kwargs.setdefault('dump_file', ir_artifact_dir + '/packages/yum/yum_dump.out')
    kwargs.setdefault('dump_file_rotate', True)
    kwargs.setdefault('to_console', False)

    cmd = 'rpm -q {package}'.format(package=package)

    ret = iexec(cmd, **kwargs)
    return ret.good_rc


def yum_install(*packages, **kwargs):
    """
    performs apt-get install on centos with various optimizations to install a list of packages
    :param packages: package list
    :param kwargs: kwargs containing flags or iexec kwargs
    :return: ret
    """
    assert running_on_centos
    clean = kwargs.pop('clean', True)
    update = kwargs.pop('update', False)
    use_sudo = kwargs.pop('use_sudo', True)

    # kwargs
    kwargs.setdefault('trace_file', ir_artifact_dir + '/packages/yum/yum_trace.out')
    kwargs.setdefault('dump_file', ir_artifact_dir + '/packages/yum/yum_dump.out')
    kwargs.setdefault('dump_file_rotate', True)
    kwargs.setdefault('to_console', False)

    # flags
    flags = []
    if kwargs.pop('yes', True):
        flags.append('-y')

    # base cmd
    if use_sudo:
        base_cmd = 'sudo yum'
    else:
        base_cmd = 'yum'

    if clean:
        iexec('{} clean all'.format(base_cmd), **kwargs)

    # update
    if update:
        iexec('{} update'.format(base_cmd), **kwargs)

    # install
    return iexec('{} install {} {}'.format(base_cmd, ' '.join(flags), ' '.join(packages)), **kwargs)


def verify_pip(get_if_needed=True, raise_on_failure=True, **kwargs):
    """
    verify that pip exists on machine
    :param get_if_needed: get pip if missing
    :param raise_on_failure: raise exception if no pip at the end
    :return: returns the pip base if all is okay, or false otherwise (or raises exception)
    """
    log.trace('verifying pip exists: get_if_needed={}'.format(get_if_needed))

    kwargs.setdefault('to_console', False)
    kwargs.setdefault('trace_file', ir_artifact_dir + '/packages/pip/verify_pip.trace.out')

    def _check_for_pip():
        for pip_base in pip_commands:
            ret = iexec('{} --version'.format(pip_base), **kwargs)
            if ret.rc == 0 and ret.contains(('pip', 'python2')):
                log.trace('pip verified: base={} out={}'.format(pip_base, ret.out))
                return pip_base
        return False

    base = _check_for_pip()
    if base is False:
        if get_if_needed and running_on_linux:
            wget_base = 'wget'
            log.warn('pip was missing, trying to install')
            iexec('{} "https://bootstrap.pypa.io/get-pip.py" -O "/tmp/get-pip.py"'.format(wget_base), **kwargs)
            get_pip_cmd = 'python "/tmp/get-pip.py"'
            iexec(get_pip_cmd, **kwargs)
            base = _check_for_pip()

    if base is False:
        if get_if_needed and running_on_linux:
            log.error('pip failed even after trying to install')
        else:
            log.error('pip is missing from machine')
        if raise_on_failure:
            raise Exception('No pip found')
        return False

    return base


def pip_cmd(*packages, **kwargs):
    """
    executes pip on current machine. Using the supplied mode and packages
    :param packages: a list of packages,
    :param kwargs: kwargs for iexec and flags
    :return:
    """

    # delete pip cache dir
    shutil.rmtree('/root/.cache/pip', ignore_errors=True)

    # test for pip
    if running_on_windows:
        pip_base = 'python -m pip'
    else:
        pip_base = verify_pip(**kwargs)

    mode = kwargs.pop('mode', 'install')

    # validate
    assert mode in ['install', 'uninstall']  # todo: expand modes

    # kwargs
    kwargs.setdefault('trace_file', ir_artifact_dir + '/packages/pip/pip_iexec_trace.out')
    kwargs.setdefault('to_console', True)

    # flags  # todo: expand flags
    flags = []
    if mode == 'install' and kwargs.pop('upgrade', True):
        flags.append('--upgrade')
    if mode == 'install' and kwargs.pop('egg', True):
        flags.append('--egg')
    if mode == 'install' and kwargs.pop('force_reinstall', True):
        flags.append('--force-reinstall')
    if mode == 'uninstall' and kwargs.pop('yes', True):
        flags.append('--yes')
    if mode == 'install' and kwargs.pop('isolated', False):
        flags.append('--isolated')
    if mode == 'install' and kwargs.pop('disable_cache', False):
        flags.append('--no-cache-dir')

    # cmd
    cmd = '{} {} {} {}'.format(pip_base, mode, ' '.join(flags), ' '.join(packages))

    return iexec(cmd, **kwargs)


__all__ = [
    'pip_cmd',
    'yum_install', 'yum_is_installed',
    'apt_get_install',
]
