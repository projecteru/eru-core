# coding:utf-8
import itertools
import logging
import os
import tempfile

from flask import abort, request
from werkzeug import secure_filename

from .bp import create_api_blueprint
from eru.async.task import (
    create_containers_with_macvlan,
    build_docker_image,
    remove_containers,
)
from eru.consts import TASK_BUILD, TASK_REMOVE, TASK_CREATE
from eru.helpers.scheduler import average_schedule, centralized_schedule
from eru.ipam import ipam
from eru.models import App, Pod, Task, Container, Host
from eru.connection import rds
from eru.utils import is_strict_url
from eru.utils.decorator import check_request_json


bp = create_api_blueprint('deploy', __name__, url_prefix='/api/deploy')
_log = logging.getLogger(__name__)
_deploy_lock = 'eru:deploy:%s:lock'


def _get_strategy(name):
    if name == 'average':
        return average_schedule
    elif name == 'centralized':
        return centralized_schedule
    abort(400, 'strategy %s not supported' % name)


def _get_app_and_version(appname, version, **kwargs):
    app = App.get_by_name(appname)
    if not app:
        abort(400, 'App `%s` not found' % appname)

    version = app.get_version(version)
    if not version:
        abort(400, 'Version `%s` not found' % version)
    return app, version


def _get_instances(podname, appname, version, **kwargs):
    pod = Pod.get_by_name(podname)
    if not pod:
        abort(400, 'Pod `%s` not found' % podname)
    app, version = _get_app_and_version(appname, version)
    return pod, app, version


@bp.route('/private/', methods=['POST'])
@check_request_json(['podname', 'appname', 'ncore', 'ncontainer', 'version', 'entrypoint', 'env'])
def create_private():
    data = request.get_json()
    pod, _, version = _get_instances(**data)

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

    task_ids, watch_keys = [], []
    with rds.lock(_deploy_lock % data['podname']):
        host_cores = _get_strategy(strategy)(pod, ncontainer, ncore, nshare, host)
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
            task_ids.append(t.id)
            watch_keys.append(t.result_key)

    return {'tasks': task_ids, 'watch_keys': watch_keys}


@bp.route('/public/', methods=['POST'])
@check_request_json(['podname', 'appname', 'ncontainer', 'version', 'entrypoint', 'env'])
def create_public():
    data = request.get_json()
    pod, _, version = _get_instances(**data)

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

    task_ids, watch_keys = [], []
    with rds.lock(_deploy_lock % data['podname']):
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
            task_ids.append(t.id)
            watch_keys.append(t.result_key)

    return {'tasks': task_ids, 'watch_keys': watch_keys}


@bp.route('/build/', methods=['PUT', 'POST'])
@check_request_json(['podname', 'appname', 'base', 'version'])
def build_image():
    data = request.get_json()
    _, version = _get_app_and_version(**data)

    base = data['base']
    if ':' not in base:
        base = base + ':latest'

    host = Host.get_random_public_host()
    if not host:
        abort(406, 'no host is available')

    task = Task.create(TASK_BUILD, version, host, {'base': base})
    build_docker_image.apply_async(
        args=(task.id, base, None),
        task_id='task:%d' % task.id
    )
    return {'task': task.id, 'watch_key': task.result_key}


@bp.route('/buildv2/', methods=['POST'])
def build_image_v2():
    # form post
    appname = request.form.get('appname', default='')
    version = request.form.get('version', default='')
    base = request.form.get('base', default='')
    if not base:
        abort(400, 'base image must be set')
    _, version = _get_app_and_version(appname, version)

    if ':' not in base:
        base = base + ':latest'

    host = Host.get_random_public_host()
    if not host:
        abort(406, 'no host is available')

    # if no artifacts.zip is set
    # ignore and just do the cloning and building
    file_path = None
    if 'artifacts.zip' in request.files:
        f = request.files['artifacts.zip']
        file_path = os.path.join(tempfile.mkdtemp(), secure_filename(f.filename))
        f.save(file_path)

    task = Task.create(TASK_BUILD, version, host, {'base': base})
    build_docker_image.apply_async(
        args=(task.id, base, file_path),
        task_id='task:%d' % task.id
    )
    return {'task': task.id, 'watch_key': task.result_key}


@bp.route('/rmcontainers/', methods=['PUT', 'POST'])
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

    task_ids, watch_keys = [], []
    for (version, host), containers in version_dict.iteritems():
        cids = [c.id for c in containers]
        task = Task.create(TASK_REMOVE, version, host, {'container_ids': cids})

        all_host_cids = [c.id for c in Container.get_multi_by_host(host) if c and c.version_id == version.id]
        need_to_delete_image = set(cids) == set(all_host_cids)

        remove_containers.apply_async(
            args=(task.id, cids, need_to_delete_image),
            task_id='task:%d' % task.id
        )
        task_ids.append(task.id)
        watch_keys.append(task.result_key)
    return {'tasks': task_ids, 'watch_keys': watch_keys}


@bp.route('/rmversion/', methods=['PUT', 'POST'])
@check_request_json(['podname', 'appname', 'version'])
def offline_version():
    data = request.get_json()
    pod, _, version = _get_instances(**data)

    d = {}
    for container in version.containers.all():
        d.setdefault(container.host, []).append(container)

    task_ids, watch_keys = [], []
    for host, containers in d.iteritems():
        cids = [c.id for c in containers]
        task = Task.create(TASK_REMOVE, version, host, {'container_ids': cids})
        remove_containers.apply_async(
            args=(task.id, cids, True),
            task_id='task:%d' % task.id
        )
        task_ids.append(task.id)
        watch_keys.append(task.result_key)
    return {'tasks': task_ids, 'watch_keys': watch_keys}


def _create_task(version, host, ncontainer, cores, nshare, networks,
        ports, args, spec_ips, entrypoint, env, image='',
        callback_url=''):
    # host 模式不允许绑定 vlan
    entry = version.appconfig['entrypoints'][entrypoint]
    if entry.get('network_mode') == 'host':
        cidrs = []
    else:
        cidrs = [n.cidr for n in networks]

    task_props = {
        'ncontainer': ncontainer,
        'entrypoint': entrypoint,
        'env': env,
        'full_cores': [c.label for c in cores.get('full', [])],
        'part_cores': [c.label for c in cores.get('part', [])],
        'ports': ports,
        'args': args,
        'nshare': nshare,
        'networks': cidrs,
        'image': image,
        'route': entry.get('network_route', ''),
        'callback_url': callback_url,
    }
    task = Task.create(TASK_CREATE, version, host, task_props)
    if not task:
        return None

    try:
        create_containers_with_macvlan.apply_async(
            args=(task.id, ncontainer, nshare, cores, cidrs, spec_ips),
            task_id='task:%d' % task.id
        )
    except Exception as e:
        _log.exception(e)
        host.release_cores(cores)
    return task
