#! /usr/bin/env python

# Lib Imports
from exec_utils import iexec
from file_utils import check_makedir, write_to_tmp_file

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.ssh')


def sftp_download(hostname, username, password, remote_path, local_path, **kwargs):
    """
    downloads from sftp server
    :param hostname:
    :param username:
    :param password:
    :param remote_path:
    :param local_path:
    :param kwargs:
    :return:
    """
    assert running_on_linux
    sftp_options = ['-o StrictHostKeyChecking=no']  # todo: dynamic options creation

    kwargs.setdefault('dump_file', ir_log_dir + '/sftp_download.txt')
    kwargs.setdefault('dump_file_rotate', True)

    check_makedir(os.path.dirname(local_path))

    cmd = 'sshpass -p {password} sftp {options} {username}@{hostname}:{remote_path} {local_path}'.format(
        hostname=hostname,
        username=username,
        password=password,
        remote_path=remote_path,
        local_path=local_path,
        options=' '.join(sftp_options),
    )

    ret = iexec(cmd, **kwargs)

    return ret


def sftp_upload(hostname, username, private_key_path, local_path, remote_path, **kwargs):
    """
    uploads to sftp server
    :param hostname:
    :param username:
    :param private_key_path:
    :param local_path:
    :param remote_path:
    :param kwargs:
    :return:
    """
    assert running_on_linux
    sftp_options = ['-o StrictHostKeyChecking=no']  # todo: dynamic options creation

    kwargs.setdefault('dump_file', ir_log_dir + '/sftp_upload.txt')
    kwargs.setdefault('dump_file_rotate', True)

    # create batch_file
    batch_command = 'put {local} {remote}'.format(local=local_path, remote=remote_path)
    batch_file_path = write_to_tmp_file(batch_command)

    cmd = 'sftp -b {batch_file} -i {identity_file} {options} {username}@{hostname}'.format(
        hostname=hostname,
        username=username,
        batch_file=batch_file_path,
        identity_file=private_key_path,
        options=' '.join(sftp_options),
    )

    ret = iexec(cmd, **kwargs)

    return ret


__all__ = [
    'sftp_download', 'sftp_upload',
]
