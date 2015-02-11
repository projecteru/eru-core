# coding: utf

from io import BytesIO
from docker import Client
from itertools import chain, izip

from res.ext.common import random_string


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
    # 据说这个 host.addr 就是类似 10.1.201.46:7777 的 string
    base_url = 'tcp://%s' % host.addr
    return Client(base_url=base_url)


def build_image(host, version, base):
    # TODO use context_dir
    """
    用 host 机器, 以 base 为基础镜像, 为 version 构建
    一个稍后可以运行的镜像.
    """
    client = _docker_client(host)
    appname = version.appconfig.appname
    build_cmd = version.appconfig.build
    repo = '{0}/{1}'.format(REGISTRY_ENDPOINT, appname)
    tag = '{0}:{1}'.format(repo, version.short_sha)

    dockerfile = BytesIO(
        DOCKER_FILE_TEMPLATE.format(
            base=base, git_url=version.application.git,
            appname=appname, sha1=version.sha, build_cmd=build_cmd
        )
    )

    build_gen = client.build(fileobj=dockerfile, rm=True, tag=tag)
    push_gen = client.push(repo, tag=version.sha[:7], stream=True, insecure_registry=True)
    return chain(build_gen, push_gen)


def create_containers(host, version, entrypoint, env, ncontainer, cores=[], ports=[], daemon=False):
    # TODO now daemon is not actually used
    """
    在 host 机器上, 用 entrypoint 在 env 下运行 ncontainer 个容器.
    这些容器可能占用 cores 这些核, 以及 ports 这些端口.
    daemon 用来指定这些容器的监控方式, 暂时没有用.
    """
    if len(cores) and len(ports) and not (len(cores) == len(ports) == ncontainer):
        return []

    client = _docker_client(host)
    appconfig = version.appconfig
    resconfig = version.get_resource_config(env)

    appname = appconfig.appname
    image = '{0}/{1}:{2}'.format(REGISTRY_ENDPOINT, appname, version.short_sha)
    cmd = appconfig.entrypoints[entrypoint]

    # build name
    # {appname}_{entrypoint}_{ident_id}
    container_name = '_'.join([appname, entrypoint, random_string(6)])

    env = {
        'NBE_RUNENV': env.upper(),
        'NBE_POD': host.pod.name,
        'NBE_PERMDIR': '/%s/permdir' % appname,
    }
    env.update(resconfig.to_env_dict(appname))

    volumes = ['/%s/permdir' % appname, ]
    user = version.app_id # 可以控制从多少开始
    working_dir = '/%s' % appname
    ports = [appconfig.port, ] if appconfig.port else None

    containers = []
    if cores and ports:
        for core, port in izip(cores, ports):
            cpuset = core.label
            container = client.create_container(image=image, command=cmd, user=user, environment=env,
                    volumes=volumes, name=container_name, cpuset=cpuset, working_dir=working_dir, ports=ports)
            # start options
            # port binding and volume binding
            port_bindings = {appconfig.port: port.port}
            binds = {'/mnt/mfs/permdir/%s' % appname: {'bind': '/%s/permdir' % appname, 'ro': False}}
            client.start(container=container['Id'], port_bindings=port_bindings, binds=binds)
            containers.append(container['Id'])
    elif ncontainer:
        for _, port in izip(ncontainer, ports):
            container = client.create_container(image=image, command=cmd, user=user, environment=env,
                    volumes=volumes, name=container_name, cpuset='', working_dir=working_dir, ports=ports)
            # start options
            # port binding and volume binding
            port_bindings = {appconfig.port: port.port}
            binds = {'/mnt/mfs/permdir/%s' % appname: {'bind': '/%s/permdir' % appname, 'ro': False}}
            client.start(container=container['Id'], port_bindings=port_bindings, binds=binds)
            containers.append(container['Id'])
    return containers

