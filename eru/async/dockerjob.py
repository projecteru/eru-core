# coding:utf-8

import os
import docker
import logging
import zipfile
import tempfile
import contextlib

from retrying import retry
from werkzeug.security import gen_salt
from docker.utils import LogConfig, Ulimit

from eru import config
from eru.docker_client import get_docker_client
from eru.templates import template
from eru.async.utils import replace_ports
from eru.utils.ensure import ensure_dir_absent, ensure_file
from eru.helpers.cloner import clone_code

_log = logging.getLogger(__name__)


@contextlib.contextmanager
def build_image_environment(version, base, archive_file=None):
    appname = version.appconfig.appname
    build_cmds = version.appconfig.build

    if not isinstance(build_cmds, list):
        build_cmds = [build_cmds,]

    if archive_file and os.path.isfile(archive_file):
        # if archive_file is passed
        build_path = os.path.dirname(archive_file)
        code_path = os.path.join(build_path, appname)
        f = zipfile.ZipFile(archive_file)
        f.extractall(code_path)
    else:
        # checkout code of version @ version.short_sha
        build_path = tempfile.mkdtemp()
        code_path = os.path.join(build_path, appname)
        clone_code(version.app.git, code_path, version.short_sha, branch=None)

    # remove git history
    ensure_dir_absent(os.path.join(code_path, '.git'))

    # launcher script
    entry = 'exec sudo -E -u %s $@' % appname
    entry_root = 'exec $@'
    launcher = template.render_template('launcher.jinja', entrypoint=entry)
    launcheroot = template.render_template('launcher.jinja', entrypoint=entry_root)
    ensure_file(os.path.join(build_path, 'launcher'), content=launcher, mode=0755)
    ensure_file(os.path.join(build_path, 'launcheroot'), content=launcheroot, mode=0755)

    # build dockerfile
    dockerfile = template.render_template(
        'dockerfile.jinja', base=base, appname=appname,
        build_cmds=build_cmds, user_id=version.user_id)
    ensure_file(os.path.join(build_path, 'Dockerfile'), content=dockerfile)

    yield build_path

    # clean build dir
    ensure_dir_absent(build_path)


def build_image(host, version, base, file_path=None):
    """
    用 host 机器, 以 base 为基础镜像, 为 version 构建
    一个稍后可以运行的镜像.
    """
    client = get_docker_client(host.addr)
    appname = version.app.name
    repo = '{0}/{1}'.format(config.DOCKER_REGISTRY, appname)
    tag = '{0}:{1}'.format(repo, version.short_sha)

    with build_image_environment(version, base, file_path) as build_path:
        return client.build(path=build_path, rm=True, forcerm=True, tag=tag)


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
        cores=None, ports=None, args=None, cpu_shares=1024, image='', need_network=False):
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
    if not is_raw:
        starter = 'launcheroot' if entry.get('privileged', '') else 'launcher'
        network = 'network' if need_network else 'nonetwork'
        cmd = '/usr/local/bin/%s %s %s' % (starter, network, cmd)

    network_mode = entry.get('network_mode', config.DOCKER_NETWORK_MODE)
    mem_limit = entry.get('mem_limit', 0)
    restart_policy = {'MaximumRetryCount': 3, 'Name': entry.get('restart', 'no')} # could be no/always/on-failure

    # raw 模式下可以选择暴露端口
    def get_ports(expose):
        inport, hostport = expose.split(':')
        return int(inport), int(hostport)

    exposes = [get_ports(expose) for expose in entry.get('exposes', [])]
    exposed_ports = None
    port_bindings = None
    if is_raw and exposes:
        exposed_ports = [p for p, _ in exposes]
        port_bindings = dict(exposes)

    if not image:
        image = '{0}/{1}:{2}'.format(config.DOCKER_REGISTRY, appname, version.short_sha)

    if image not in local_images:
        repo, tag = image.split(':', 1)
        for line in client.pull(repo, tag, stream=True, insecure_registry=config.DOCKER_REGISTRY_INSECURE):
            _log.info(line)

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

    if config.ERU_CONTAINER_PERMDIR and entry.get('permdir', ''):
        permdir = config.ERU_CONTAINER_PERMDIR % appname
        env_dict['ERU_PERMDIR'] = permdir
        volumes.append(permdir)
        binds[config.ERU_HOST_PERMDIR % appname] =  {'bind': permdir, 'ro': False}

    extra_hosts = entry.get('hosts', None)

    # container name: {appname}_{entrypoint}_{ident_id}
    container_name = '_'.join([appname, entrypoint, gen_salt(6)])
    # cpuset: '0,1,2,3'
    cpuset = ','.join([c.label for c in cores])
    # host_config, include log_config
    host_config = client.create_host_config(
        binds=binds,
        network_mode=network_mode,
        log_config=LogConfig(type=config.DOCKER_LOG_DRIVER),
        ulimits=[Ulimit(name='nofile', soft=65535, hard=65535)],
        restart_policy=restart_policy,
        mem_limit=mem_limit,
        port_bindings=port_bindings,
        extra_hosts=extra_hosts,
    )
    container = client.create_container(
        image=image,
        command=cmd,
        environment=env_dict,
        name=container_name,
        cpuset=cpuset,
        working_dir=None if is_raw else '/%s' % appname,
        network_disabled=config.DOCKER_NETWORK_DISABLED,
        volumes=volumes,
        host_config=host_config,
        cpu_shares=cpu_shares,
        ports=exposed_ports,
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
                _log.info('%s not found, just delete it' % c.container_id)
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
                _log.info('%s not found, just delete it' % cid)
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
            _log.info('%s not found, just delete it' % image)
        else:
            raise
