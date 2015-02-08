# coding: utf

from cStringIO import StringIO
from itertools import chain
from docker import Client
from docker.utils import create_host_config

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


def _client(host):
    base_url = 'tcp://{host.addr}:1111'.format(host=host)
    return Client(base_url=base_url)


def build_image(host, version, base):
    c = _client(host)
    appname = version.name
    build_cmd = ' '.join(version.appconfig.build)
    repo = '%s/%s' % (REGISTRY_ENDPOINT, appname)
    tag = '%s:%s' % (repo, version.sha[:7])

    dockerfile = StringIO(DOCKER_FILE_TEMPLATE.format(
        base=base, git_url=version.application.git,
        appname=appname, sha1=version.sha, build_cmd=build_cmd))

    build_gen = c.build(fileobj=dockerfile, rm=True, tag=tag)
    # r = c.build(fileobj=dockerfile, rm=True, tag=tag)
    # for line in r:
    #     yield line

    push_gen = c.push(repo, tag=version.sha[:7], stream=True, insecure_registry=True)
    # r = c.push(repo, tag=version.sha[:7], stream=True, insecure_registry=True)
    # for line in r:
    #     yield line

    return chain(build_gen, push_gen)


def create_container(host, version, is_test=False):
    c = _client(host)
    appname = version.name
    image = '%s/%s:%s' % (REGISTRY_ENDPOINT, appname, version.sha[:7])
    cmd = version.appconfig.test if is_test else version.appconfig.cmd
    ident_id = random_string(6) if is_test else ''
    container_name = '%s_%s' % (appname, ident_id) if is_test else appname
    env = {
        'NBE_RUNENV': 'TEST' if is_test else 'PROD',
        'NBE_POD': host.pod.name,
        'NBE_PERMDIR': '/%s/permdir' % appname,
    }
    volumes = ['/mnt/mfs/permdir/%s' % appname, '/tmp/%s_config.yaml' % appname]
    user = version.aid # 可以控制从多少开始
    cpuset = '' # 有才设置
    working_dir = '/%s' % appname

    container = c.create_container(image=image, command=cmd, user=user, environment=env,
            volumes=volumes, name=container_name, cpuset=cpuset, working_dir=working_dir)
    return c.start(container=container['Id'], binds=None)
