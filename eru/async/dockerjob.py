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

def create_one_container(host, version, entrypoint, env='prod', cores=None):
    if cores is None:
        cores = []

    client = get_docker_client(host.addr)
    local_images = {r['RepoTags'][0] for r in client.images()}

    appconfig = version.appconfig
    appname = appconfig.appname
    entry = appconfig.entrypoints[entrypoint]
    envconfig = version.get_resource_config(env)

    image = '{0}/{1}:{2}'.format(settings.DOCKER_REGISTRY, appname, version.short_sha)
    if image not in local_images:
        repo = '{0}/{1}'.format(settings.DOCKER_REGISTRY, appname)
        for line in client.pull(repo, tag=version.short_sha, stream=True,
                                insecure_registry=settings.DOCKER_REGISTRY_INSECURE):
            print line

    env_dict = {
        'APP_NAME': appname,
        'ERU_RUNENV': env.upper(),
        'ERU_POD': host.pod.name,
        'ERU_HOST': host.name,
    }
    env_dict.update(envconfig.to_env_dict())

    volumes, binds = None, None
    if settings.ERU_CONTAINER_PERMDIR:
        permdir = settings.ERU_CONTAINER_PERMDIR % appname
        env_dict['ERU_PERMDIR'] = permdir
        volumes = [permdir,]
        binds = {settings.ERU_HOST_PERMDIR % appname: {'bind': permdir, 'ro': False}}

    # container name: {appname}_{entrypoint}_{ident_id}
    container_name = '_'.join([appname, entrypoint, random_string(6)])
    # cpuset: '0,1,2,3'
    cpuset = ','.join([c.label for c in cores])
    container = client.create_container(
        image=image,
        command=entry['cmd'],
        user=version.app_id,
        environment=env_dict,
        name=container_name,
        cpuset=cpuset,
        working_dir='/%s' % appname,
        network_disabled=settings.DOCKER_NETWORK_DISABLED,
        volumes=volumes,
    )
    container_id = container['Id']

    client.start(container=container_id, network_mode=settings.DOCKER_NETWORK_MODE, binds=binds)
    return container_id, container_name

def execute_container(host, container_id, cmd):
    client = get_docker_client(host.addr)
    exec_id = client.exec_create(container_id, cmd)
    return client.exec_start(exec_id)

def start_containers(containers, host):
    """启动这个host上的这些容器"""
    client = get_docker_client(host.addr)
    for c in containers:
        client.start(c.container_id)

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

def remove_container_by_cid(cids, host):
    client = get_docker_client(host.addr)
    for cid in cids:
        client.stop(cid)
        client.remove_container(cid)

def remove_image(version, host):
    """在host上删除掉version的镜像"""
    client = get_docker_client(host.addr)
    appconfig = version.appconfig
    appname = appconfig.appname
    image = '{0}/{1}:{2}'.format(settings.DOCKER_REGISTRY, appname, version.short_sha)
    client.remove_image(image)

