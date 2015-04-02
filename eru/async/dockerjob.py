#!/usr/bin/python
#coding:utf-8

import os
import tempfile
import pygit2
import contextlib

from res.ext.common import random_string

from eru.common import settings
from eru.common.clients import get_docker_client
from eru.utils.ensure import ensure_dir_absent, ensure_file


DOCKER_FILE_TEMPLATE = '''
FROM {base}
ENV ERU 1
ADD {appname} /{appname}
WORKDIR /{appname}
RUN {build_cmd}
'''


@contextlib.contextmanager
def build_image_environment(version, base, rev):
    appname = version.appconfig.appname
    build_cmd = version.appconfig.build

    if isinstance(build_cmd, list):
        # 好 tricky...
        build_cmd = '\nRUN '.join(build_cmd)

    # checkout code of version @ rev
    build_path = tempfile.mkdtemp()
    clone_path = os.path.join(build_path, appname)
    repo = pygit2.clone_repository(version.app.git, clone_path)
    repo.checkout('HEAD')
    o = repo.revparse_single(rev)
    repo.checkout_tree(o.tree)

    # remove git history
    ensure_dir_absent(os.path.join(clone_path, '.git'))

    # build dockerfile
    dockerfile = DOCKER_FILE_TEMPLATE.format(
        base=base, appname=appname, build_cmd=build_cmd
    )
    ensure_file(os.path.join(build_path, 'Dockerfile'), content=dockerfile)

    # TODO 这里可能需要加上静态文件的处理
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
    repo = '{0}/{1}'.format(settings.DOCKER_REGISTRY, appname)
    rev = version.short_sha
    tag = '{0}:{1}'.format(repo, rev)

    with build_image_environment(version, base, rev) as build_path:
        return client.build(path=build_path, rm=True, tag=tag)


def push_image(host, version):
    client = get_docker_client(host.addr)
    appname = version.app.name
    repo = '{0}/{1}'.format(settings.DOCKER_REGISTRY, appname)
    rev = version.short_sha
    return client.push(repo, tag=rev, stream=True, insecure_registry=settings.DOCKER_REGISTRY_INSECURE)


def pull_image(host, repo, tag):
    client = get_docker_client(host.addr)
    return client.pull(repo, tag=tag, stream=True, insecure_registry=settings.DOCKER_REGISTRY_INSECURE)


def create_containers(host, version, entrypoint, env, ncontainer, cores=[], ports=[], daemon=False):
    # TODO now daemon is not actually used
    """
    在 host 机器上, 用 entrypoint 在 env 下运行 ncontainer 个容器.
    这些容器可能占用 cores 这些核, 以及 ports 这些端口.
    daemon 用来指定这些容器的监控方式, 暂时没有用.
    """
    client = get_docker_client(host.addr)
    appconfig = version.appconfig
    envconfig = version.get_resource_config(env)

    appname = appconfig.appname
    image = '{0}/{1}:{2}'.format(settings.DOCKER_REGISTRY, appname, version.short_sha)
    entry = appconfig.entrypoints[entrypoint]

    repo = '{0}/{1}'.format(settings.DOCKER_REGISTRY, appname)

    cmd = entry['cmd']
    entryports = entry.get('ports', [])

    volumes, binds = None, None
    env_dict = {
        'APP_NAME': appname,
        'ERU_RUNENV': env.upper(),
        'ERU_POD': host.pod.name,
    }
    env_dict.update(envconfig.to_env_dict())

    # 设置留空表示不 mount 任何 permdir 进来
    if settings.ERU_CONTAINER_PERMDIR:
        env_dict['ERU_PERMDIR'] = settings.ERU_CONTAINER_PERMDIR % appname
        volumes = [settings.ERU_CONTAINER_PERMDIR % appname, ]
        binds = {settings.ERU_HOST_PERMDIR % appname: {'bind': settings.ERU_CONTAINER_PERMDIR % appname, 'ro': False}}

    user = version.app_id # 可以控制从多少开始
    working_dir = '/%s' % appname
    container_ports = [tuple(e.split('/')) for e in entryports] if entryports else None # ['4001/tcp', '5001/udp']

    for line in client.pull(repo, tag=version.short_sha, stream=True, insecure_registry=settings.DOCKER_REGISTRY_INSECURE):
        #TODO 接了日志输出后写入 redis
        print line

    containers = []
    cores_per_container = len(cores) / ncontainer
    for index in xrange(ncontainer):
        # build name
        # {appname}_{entrypoint}_{ident_id}
        container_name = '_'.join([appname, entrypoint, random_string(6)])
        used_cores = cores[index*cores_per_container:(index+1)*cores_per_container] if cores else ''
        cpuset = ','.join([c.label for c in used_cores])
        container = client.create_container(
            image=image, command=cmd, user=user, environment=env_dict,
            volumes=volumes, name=container_name, cpuset=cpuset,
            working_dir=working_dir, ports=container_ports,
        )
        container_id = container['Id']

        # start options
        # port binding and volume binding
        expose_ports = [ports.pop(0) for _ in entryports]
        ports_bindings = dict(zip(entryports, [p.port for p in expose_ports])) if expose_ports else None

        client.start(container=container_id, port_bindings=ports_bindings, binds=binds)

        containers.append((container_id, container_name, entrypoint, used_cores, expose_ports))
    return containers


def stop_containers(containers, host):
    """停止这个host上的这些容器"""
    client = get_docker_client(host.addr)
    for c in containers:
        client.stop(c.container_id)


def remove_host_containers(containers, host):
    """删除这个host上的这些容器"""
    client = get_docker_client(host.addr)
    for c in containers:
        if c.is_alive:
            client.stop(c.container_id)
        client.remove_container(c.container_id)


def remove_image(version, host):
    """在host上删除掉version的镜像"""
    client = get_docker_client(host.addr)
    appconfig = version.appconfig
    appname = appconfig.appname
    image = '{0}/{1}:{2}'.format(settings.DOCKER_REGISTRY, appname, version.short_sha)
    client.remove_image(image)

