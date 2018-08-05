#! /usr/bin/env python

# Lib Imports
from exec_utils import iexec
from file_utils import check_makedir

# irtools Imports
from irtools import *

# logging
log = logging.getLogger('irtools.utils.docker')
docker_trace_log = ir_log_dir + '/docker_trace.log'


def copy_from_docker(container_id, src, dst, **kwargs):
    kwargs.setdefault('to_console', False)
    kwargs.setdefault('trace_file', docker_trace_log)
    log.debug('copying from docker: id={} src={} dst={}'.format(container_id, src, dst))
    if os.path.isdir(dst):
        dir_to_make = dst
    else:
        dir_to_make = os.path.dirname(dst)
    check_makedir(dir_to_make)
    cmd = 'docker cp {container_id}:{src} {dst}'.format(container_id=container_id, src=src, dst=dst)
    return iexec(cmd, **kwargs)


def copy_to_docker(container_id, src, dst, **kwargs):
    kwargs.setdefault('to_console', False)
    kwargs.setdefault('trace_file', docker_trace_log)
    log.debug('copying to docker: id={} src={} dst={}'.format(container_id, src, dst))
    cmd = 'docker cp {src} {container_id}:{dst}'.format(container_id=container_id, src=src, dst=dst)
    return iexec(cmd, **kwargs)


def remove_docker_container(container_id, force=False, volumes=True, **kwargs):
    kwargs.setdefault('to_console', False)
    kwargs.setdefault('trace_file', docker_trace_log)
    cmd = 'docker rm'
    if force:
        cmd = '{} --force'.format(cmd)
    if volumes:
        cmd = '{} --volumes'.format(cmd)
    cmd = '{} {}'.format(cmd, container_id)
    return iexec(cmd, **kwargs)


def remove_docker_image(image_id, force=False, **kwargs):
    kwargs.setdefault('to_console', False)
    kwargs.setdefault('trace_file', docker_trace_log)
    cmd = 'docker rmi'
    if force:
        cmd = '{} --force'.format(cmd)
    cmd = '{} {}'.format(cmd, image_id)
    return iexec(cmd, **kwargs)


def get_container_id_from_composition_service(composition_file, service_name, **kwargs):
    log.trace('getting container id from composition service: composition={} service={}'.format(
        composition_file, service_name
    ))

    cmd = 'docker-compose -f {composition_file} ps -q {service_name}'.format(
        composition_file=composition_file, service_name=service_name)
    ret = iexec(cmd, **kwargs)

    container_id = ret.out_string.strip()
    # todo: better detection of container id
    if not container_id:
        raise RuntimeError('Could not fetch container_id for composition service: composition={} service={}'.format(
            composition_file, service_name
        ))

    log.trace('found container id for composition service: container_id={} composition={} service={}'.format(
        container_id, composition_file, service_name))
    return container_id


def docker_compose_exec(composition_file, service_name, cmd, **kwargs):
    container_id = get_container_id_from_composition_service(composition_file, service_name, **kwargs)
    return docker_exec(container_id, cmd, **kwargs)


def docker_exec(container_id, cmd, **kwargs):
    log.debug('performing docker exec: id={} cmd={}'.format(container_id, cmd))
    return iexec('docker exec {id} {cmd}'.format(id=container_id, cmd=cmd), **kwargs)


__all__ = [
    'copy_from_docker', 'copy_to_docker',
    'remove_docker_container', 'remove_docker_image',
    'get_container_id_from_composition_service',
    'docker_exec', 'docker_compose_exec',
]
