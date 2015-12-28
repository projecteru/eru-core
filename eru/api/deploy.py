# coding:utf-8

import logging
import itertools

from flask import abort, request

from eru.utils import is_strict_url
from eru.utils.decorator import check_request_json

from eru import consts
from eru.ipam import ipam
from eru.clients import rds
from eru.models import App, Group, Pod, Task, Container, Host
from eru.async.task import (
    create_containers_with_macvlan,
    build_docker_image,
    remove_containers,
)
from eru.helpers.scheduler import average_schedule, centralized_schedule

from .bp import create_api_blueprint

bp = create_api_blueprint('deploy', __name__, url_prefix='/api/deploy')
logger = logging.getLogger(__name__)


def _get_strategy(name):
    if name == 'average':
        return average_schedule
    elif name == 'centralized':
        return centralized_schedule
    abort(400, 'strategy %s not supported' % name)


@bp.route('/private/<group_name>/<pod_name>/<appname>', methods=['POST', ])
@check_request_json(['ncore', 'ncontainer', 'version', 'entrypoint', 'env'])
def create_private(group_name, pod_name, appname):
    data = request.get_json()
    vstr = data['version']
    group, pod, _, version = validate_instance(group_name, pod_name, appname, vstr)

    # TODO check if group has this pod
    ncore, nshare = pod.get_core_allocation(float(data['ncore']))
    ports = data.get('ports', [])
    args = data.get('args', [])
    strategy = data.get('strategy', 'average')

    callback_url = data.get('callback_url', '')
    if callback_url and not is_strict_url(callback_url):
        abort(400, 'callback_url must start with http:// or https://')

    ncontainer = int(data['ncontainer'])
    if not ncontainer:
        abort(400, 'ncontainer must be > 0')

    networks = [ipam.get_pool(n) for n in data.get('networks', [])]
    spec_ips = data.get('spec_ips', [])
    appconfig = version.appconfig

    entrypoint = data['entrypoint']
    if entrypoint not in appconfig.entrypoints:
        abort(400, 'Entrypoint %s not in app.yaml' % entrypoint)

    hostname = data.get('hostname', '')
    host = hostname and Host.get_by_name(hostname) or None
    if host and not (host.group_id == group.id and host.pod_id == pod.id):
        abort(400, 'Host must belong to this pod and group')

    ts, keys = [], []
    with rds.lock('%s:%s' % (group_name, pod_name)):
        host_cores = _get_strategy(strategy)(group, pod, ncontainer, ncore, nshare, host)
        if not host_cores:
            abort(400, 'Not enough core resources')

        for (host, container_count), cores in host_cores.iteritems():
            t = _create_task(
                version,
                host,
                container_count,
                cores,
                nshare,
                networks,
                ports,
                args,
                spec_ips,
                entrypoint,
                data['env'],
                image=data.get('image', ''),
                callback_url=callback_url,
            )
            if not t:
                continue

            host.occupy_cores(cores, nshare)
            ts.append(t.id)
            keys.append(t.result_key)

    return {'r': 0, 'msg': 'ok', 'tasks': ts, 'watch_keys': keys}


@bp.route('/public/<group_name>/<pod_name>/<appname>', methods=['POST', ])
@check_request_json(['ncontainer', 'version', 'entrypoint', 'env'])
def create_public(group_name, pod_name, appname):
    data = request.get_json()
    vstr = data['version']
    group, pod, _, version = validate_instance(group_name, pod_name, appname, vstr)

    ports = data.get('ports', [])
    args = data.get('args', [])

    callback_url = data.get('callback_url', '')
    if callback_url and not is_strict_url(callback_url):
        abort(400, 'callback_url must starts with http:// or https://')

    networks = [ipam.get_pool(n) for n in data.get('networks', [])]
    spec_ips = data.get('spec_ips', [])
    appconfig = version.appconfig

    ncontainer = int(data['ncontainer'])
    if not ncontainer:
        abort(400, 'ncontainer must be > 0')

    entrypoint = data['entrypoint']
    if entrypoint not in appconfig.entrypoints:
        abort(400, 'Entrypoint %s not in app.yaml' % entrypoint)

    ts, keys = [], []
    with rds.lock('%s:%s' % (group_name, pod_name)):
        hosts = pod.get_free_public_hosts(ncontainer)
        for host in itertools.islice(itertools.cycle(hosts), ncontainer):
            t = _create_task(
                version,
                host,
                1,
                {},
                0,
                networks,
                ports,
                args,
                spec_ips,
                data['entrypoint'],
                data['env'],
                image=data.get('image', ''),
                callback_url=callback_url,
            )
            if not t:
                continue
            ts.append(t.id)
            keys.append(t.result_key)

    return {'r':0, 'msg': 'ok', 'tasks': ts, 'watch_keys': keys}


@bp.route('/build/<group_name>/<pod_name>/<appname>', methods=['PUT', 'POST', ])
@check_request_json(['base', 'version'])
def build_image(group_name, pod_name, appname):
    data = request.get_json()
    group, pod, _, version = validate_instance(group_name, pod_name, appname, data['version'])

    base = data['base']
    if ':' not in base:
        base = base + ':latest'

    host = Host.get_random_public_host() or pod.get_random_host()
    if not host:
        return {'r': 1, 'msg': 'no host is available'}

    task = Task.create(consts.TASK_BUILD, version, host, {'base': base})
    build_docker_image.apply_async(
        args=(task.id, base),
        task_id='task:%d' % task.id
    )
    return {'r': 0, 'msg': 'ok', 'task': task.id, 'watch_key': task.result_key}


@bp.route('/rmcontainers/', methods=['PUT', 'POST', ])
@check_request_json(['cids'])
def rm_containers():
    cids = request.get_json()['cids']

    if not all(len(cid) >= 7 for cid in cids):
        abort(400, 'must given at least 7 chars for container_id')

    version_dict = {}
    for cid in cids:
        container = Container.get_by_container_id(cid)
        if not container:
            continue
        version_dict.setdefault((container.version, container.host), []).append(container)

    ts, watch_keys = [], []
    for (version, host), containers in version_dict.iteritems():
        cids = [c.id for c in containers]
        task = Task.create(consts.TASK_REMOVE, version, host, {'container_ids': cids})

        all_host_cids = [c.id for c in Container.get_multi_by_host(host) if c and c.version_id == version.id]
        need_to_delete_image = set(cids) == set(all_host_cids)

        remove_containers.apply_async(
            args=(task.id, cids, need_to_delete_image),
            task_id='task:%d' % task.id
        )
        ts.append(task.id)
        watch_keys.append(task.result_key)
    return {'r': 0, 'msg': 'ok', 'tasks': ts, 'watch_keys': watch_keys}


@bp.route('/rmversion/<group_name>/<pod_name>/<appname>', methods=['PUT', 'POST', ])
@check_request_json(['version'])
def offline_version(group_name, pod_name, appname):
    data = request.get_json()
    group, pod, _, version = validate_instance(group_name, pod_name, appname, data['version'])

    d = {}
    for container in version.containers.all():
        d.setdefault(container.host, []).append(container)

    ts, keys = [], []
    for host, containers in d.iteritems():
        cids = [c.id for c in containers]
        task = Task.create(consts.TASK_REMOVE, version, host, {'container_ids': cids})
        remove_containers.apply_async(
            args=(task.id, cids, True),
            task_id='task:%d' % task.id
        )
        ts.append(task.id)
        keys.append(task.result_key)
    return {'r': 0, 'msg': 'ok', 'tasks': ts, 'watch_keys': keys}


def validate_instance(group_name, pod_name, appname, version):
    group = Group.get_by_name(group_name)
    if not group:
        abort(400, 'Group `%s` not found' % group_name)

    pod = Pod.get_by_name(pod_name)
    if not pod:
        abort(400, 'Pod `%s` not found' % pod_name)

    app = App.get_by_name(appname)
    if not app:
        abort(400, 'App `%s` not found' % appname)

    version = app.get_version(version)
    if not version:
        abort(400, 'Version `%s` not found' % version)

    return group, pod, app, version


def _create_task(version, host, ncontainer, cores, nshare, networks,
        ports, args, spec_ips, entrypoint, env, image='',
        callback_url=''):
    # host 模式不允许绑定 vlan
    entry = version.appconfig['entrypoints'][entrypoint]
    if entry.get('network_mode') == 'host':
        network_ids = []
    else:
        network_ids = [n.id for n in networks]

    task_props = {
        'ncontainer': ncontainer,
        'entrypoint': entrypoint,
        'env': env,
        'full_cores': [c.label for c in cores.get('full', [])],
        'part_cores': [c.label for c in cores.get('part', [])],
        'ports': ports,
        'args': args,
        'nshare': nshare,
        'networks': network_ids,
        'image': image,
        'route': entry.get('network_route', ''),
        'callback_url': callback_url,
    }
    task = Task.create(consts.TASK_CREATE, version, host, task_props)
    if not task:
        return None

    try:
        create_containers_with_macvlan.apply_async(
            args=(task.id, ncontainer, nshare, cores, network_ids, spec_ips),
            task_id='task:%d' % task.id
        )
    except Exception as e:
        logger.exception(e)
        host.release_cores(cores)
    return task
