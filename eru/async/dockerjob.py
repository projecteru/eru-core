# coding:utf-8

import os
import logging
import tempfile
import pygit2
import contextlib

import docker
from docker.utils import create_host_config, LogConfig, Ulimit
from retrying import retry

from res.ext.common import random_string

from eru import config
from eru.clients import get_docker_client
from eru.templates import template
from eru.utils.ensure import ensure_dir_absent, ensure_file
from eru.async.utils import replace_ports

logger = logging.getLogger(__name__)

@contextlib.contextmanager
def build_image_environment(version, base, rev):
    appname = version.appconfig.appname
    build_cmds = version.appconfig.build

    if not isinstance(build_cmds, list):
        build_cmds = [build_cmds,]

    # checkout code of version @ rev
    build_path = tempfile.mkdtemp()
    clone_path = os.path.join(build_path, appname)
    repo = pygit2.clone_repository(version.app.git, clone_path)
    repo.checkout('HEAD')
    o = repo.revparse_single(rev)
    repo.checkout_tree(o.tree)

    # remove git history
    ensure_dir_absent(os.path.join(clone_path, '.git'))

    # launcher script
    launcher = template.render_template('launcher.jinja', appname=appname)
    ensure_file(os.path.join(build_path, 'launcher'), content=launcher, mode=0755)

    # build dockerfile
    dockerfile = template.render_template(
        'dockerfile.jinja', base=base, appname=appname,
        build_cmds=build_cmds, user_id=version.user_id)
    ensure_file(os.path.join(build_path, 'Dockerfile'), content=dockerfile)

    yield build_path

    # clean build dir
    ensure_dir_absent(build_path)

def build_image(host, version, base):
    """
    用 host 机器, 以 base 为基础镜像, 为 version 构建
    一个稍后可以运行的镜像.
    """
    client = get_docker_client(host.addr)
    appname = version.app.name
    repo = '{0}/{1}'.format(config.DOCKER_REGISTRY, appname)
    rev = version.short_sha
    tag = '{0}:{1}'.format(repo, rev)

    with build_image_environment(version, base, rev) as build_path:
        return client.build(path=build_path, rm=True, tag=tag)

def push_image(host, version):
    client = get_docker_client(host.addr)
    appname = version.app.name
    repo = '{0}/{1}'.format(config.DOCKER_REGISTRY, appname)
    rev = version.short_sha
    return client.push(repo, tag=rev, stream=True, insecure_registry=config.DOCKER_REGISTRY_INSECURE)

def pull_image(host, repo, tag):
    client = get_docker_client(host.addr)
    return client.pull(repo, tag=tag, stream=True, insecure_registry=config.DOCKER_REGISTRY_INSECURE)

def create_one_container(host, version, entrypoint, env='prod',
        cores=None, ports=None, args=None, cpu_shares=1024, image=''):
    # raw方式有些设定不同
    is_raw = bool(image)

    if cores is None:
        cores = []
    if ports is None:
        ports = []
    if args is None:
        args = []

    client = get_docker_client(host.addr)
    local_images = {r['RepoTags'][0] for r in client.images()}

    appconfig = version.appconfig
    appname = appconfig.appname
    entry = appconfig.entrypoints[entrypoint]
    envconfig = version.get_resource_config(env)
    # replace $port1...
    cmd = replace_ports(entry['cmd'], ports)
    # add extend arguments
    cmd = cmd + ' '.join([''] + args)

    network_mode = entry.get('network_mode', config.DOCKER_NETWORK_MODE)
    mem_limit = entry.get('mem_limit', 0)
    restart_policy = {'MaximumRetryCount': 3, 'Name': entry.get('restart', 'no')} # could be no/always/on-failure

    if not image:
        image = '{0}/{1}:{2}'.format(config.DOCKER_REGISTRY, appname, version.short_sha)

    if image not in local_images:
        repo, tag = image.split(':', 1)
        for line in client.pull(repo, tag, stream=True,
                insecure_registry=config.DOCKER_REGISTRY_INSECURE):
            print line

    env_dict = {
        'APP_NAME': appname,
        'ERU_RUNENV': env.upper(),
        'ERU_POD': host.pod.name,
        'ERU_HOST': host.name,
    }
    env_dict.update(envconfig.to_env_dict())

    volumes = ['/writable-proc/sys']
    volumes.extend(appconfig.get('volumes', []))

    binds = {'/proc/sys': {'bind': '/writable-proc/sys', 'ro': False}}
    binds.update(appconfig.get('binds', {}))

    if config.ERU_CONTAINER_PERMDIR:
        permdir = config.ERU_CONTAINER_PERMDIR % appname
        env_dict['ERU_PERMDIR'] = permdir
        volumes.append(permdir)
        binds[config.ERU_HOST_PERMDIR % appname] =  {'bind': permdir, 'ro': False}

    # container name: {appname}_{entrypoint}_{ident_id}
    container_name = '_'.join([appname, entrypoint, random_string(6)])
    # cpuset: '0,1,2,3'
    cpuset = ','.join([c.label for c in cores])
    # host_config, include log_config
    host_config = create_host_config(
        binds=binds,
        network_mode=network_mode,
        log_config=LogConfig(type=config.DOCKER_LOG_DRIVER),
        ulimits=[Ulimit(name='nofile', soft=65535, hard=65535)],
        restart_policy=restart_policy,
        mem_limit=mem_limit,
    )
    container = client.create_container(
        image=image,
        command=cmd,
        environment=env_dict,
        entrypoint=None if is_raw else '/usr/local/bin/launcher',
        name=container_name,
        cpuset=cpuset,
        working_dir=None if is_raw else '/%s' % appname,
        network_disabled=config.DOCKER_NETWORK_DISABLED,
        volumes=volumes,
        host_config=host_config,
        cpu_shares=cpu_shares,
    )
    container_id = container['Id']

    client.start(container=container_id)
    return container_id, container_name

def execute_container(host, container_id, cmd, stream=False):
    """在容器里跑一个命令, stream的话返回一个generator"""
    client = get_docker_client(host.addr)
    exec_id = client.exec_create(container_id, cmd, stream=stream)
    return client.exec_start(exec_id)

def start_containers(containers, host):
    """启动这个host上的这些容器"""
    client = get_docker_client(host.addr)
    for c in containers:
        client.start(c.container_id)

def __retry_on_api_error(e):
    return isinstance(e, docker.errors.APIError) and '500 Server Error' in str(e)

@retry(retry_on_exception=__retry_on_api_error)
def __stop_container(client, cid):
    """为什么要包一层, 因为 https://github.com/docker/docker/issues/12738 """
    client.stop(cid)

def stop_containers(containers, host):
    """停止这个host上的这些容器"""
    client = get_docker_client(host.addr)
    for c in containers:
        __stop_container(client, c.container_id)

def remove_host_containers(containers, host):
    """删除这个host上的这些容器"""
    client = get_docker_client(host.addr)
    for c in containers:
        try:
            __stop_container(client, c.container_id)
            client.remove_container(c.container_id)
        except docker.errors.APIError as e:
            if 'no such id' in str(e).lower():
                logger.info('%s not found, just delete it' % c.container_id)
                continue
            raise

def remove_container_by_cid(cids, host):
    client = get_docker_client(host.addr)
    for cid in cids:
        try:
            __stop_container(client, cid)
            client.remove_container(cid)
        except docker.errors.APIError as e:
            if 'no such id' in str(e).lower():
                logger.info('%s not found, just delete it' % cid)
                continue
            raise

def remove_image(version, host):
    """在host上删除掉version的镜像"""
    client = get_docker_client(host.addr)
    appconfig = version.appconfig
    appname = appconfig.appname
    image = '{0}/{1}:{2}'.format(config.DOCKER_REGISTRY, appname, version.short_sha)
    try:
        client.remove_image(image)
    except docker.errors.APIError as e:
        if 'no such image' in str(e).lower():
            logger.info('%s not found, just delete it' % image)
        else:
            raise
