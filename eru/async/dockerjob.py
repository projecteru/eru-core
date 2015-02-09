# coding: utf

from docker import Client
from cStringIO import StringIO
from itertools import chain

from eru.aysnc.utils import random_string


DOCKER_FILE_TEMPLATE = '''
FROM {base}
ENV NBE 1
RUN git clone {git_url} /{appname}
WORKDIR /{appname}
RUN git reset --hard {sha1}
RUN {build_cmd}
'''
REGISTRY_ENDPOINT = 'docker-registry.intra.hunantv.com'


def _docker_client(host):
    base_url = 'tcp://{host.addr}:1111'.format(host=host)
    return Client(base_url=base_url)


def build_image(host, version, base):
    """
    用 host 机器, 以 base 为基础镜像, 为 version 构建
    一个稍后可以运行的镜像.
    """
    client = _docker_client(host)
    appname = version.name
    build_cmd = version.appconfig.build
    repo = '{0}/{1}'.format(REGISTRY_ENDPOINT, appname)
    tag = '{0}:{1}'.format(repo, version.short_sha)

    dockerfile = StringIO(DOCKER_FILE_TEMPLATE.format(
        base=base, git_url=version.application.git,
        appname=appname, sha1=version.sha, build_cmd=build_cmd))

    build_gen = client.build(fileobj=dockerfile, rm=True, tag=tag)
    push_gen = client.push(repo, tag=version.sha[:7], stream=True, insecure_registry=True)
    return chain(build_gen, push_gen)


def create_container(host, version, sub, port=0, is_test=False):
    """
    在 host 机器上, 用 sub, port 作为外部端口, 创建一个 version 的实例.
    sub 定义在 app.yaml 的 commands 里, 具体可以参考 eru/models/appconfig.py.
    """
    client = _docker_client(host)
    appconfig = version.appconfig
    resconfig = version.get_resource_config('test' if is_test else 'prod')

    appname = appconfig.appname
    image = '{0}/{1}:{2}'.format(REGISTRY_ENDPOINT, appname, version.short_sha)
    cmd = version.appconfig.test if is_test else appconfig.commands[sub]

    # build name
    # 有端口暴露的: {appname}_{port}, {appname}_{subname}_{port}
    # 没有端口暴露的(daemon): {appname}_{ident_id}, {appname}_{subname}_{ident_id}
    name_parts = [appname, ]
    if sub:
        name_parts.append(sub)
    name_parts.append(str(port) if port else random_string(6))
    container_name = '_'.join(name_parts)

    env = {
        'NBE_RUNENV': 'TEST' if is_test else 'PROD',
        'NBE_POD': host.pod.name,
        'NBE_PERMDIR': '/%s/permdir' % appname,
    }
    env.update(resconfig.to_env_dict(appname))

    volumes = ['/%s/permdir' % appname, ]
    user = version.aid # 可以控制从多少开始
    cpuset = '' # 有才设置
    working_dir = '/%s' % appname
    ports = [appconfig.port, ] if appconfig.port else None

    container = client.create_container(image=image, command=cmd, user=user, environment=env,
            volumes=volumes, name=container_name, cpuset=cpuset, working_dir=working_dir, ports=ports)

    # start options
    # port binding and volume binding
    port_bindings = {appconfig.port: port}
    binds = {'/mnt/mfs/permdir/%s' % appname: {'bind': '/%s/permdir' % appname, 'ro': False}}
    return client.start(container=container['Id'], port_bindings=port_bindings, binds=binds)

