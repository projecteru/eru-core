# coding: utf-8

import logging
import geventwebsocket
from flask import Blueprint, request

from eru.models import Task, Container
from eru.utils.notify import TaskNotifier

from eru.common import code
from eru.common.clients import rds, get_docker_client

bp = Blueprint('websockets', __name__, url_prefix='/websockets')
logger = logging.getLogger(__name__)

@bp.route('/tasklog/<int:task_id>/')
def task_log(task_id):
    ws = request.environ['wsgi.websocket']

    task = Task.get(task_id)
    if not task:
        ws.close()
        logger.info('Task %s not found, close websocket' % task_id)
        return 'websocket closed'

    notifier = TaskNotifier(task)
    try:
        pub = rds.pubsub()
        pub.subscribe(task.publish_key)

        for line in notifier.get_store_logs():
            ws.send(line)

        if task.finished:
            return ''

        for line in pub.listen():
            if line['data'] == code.PUB_END_MESSAGE:
                break
            if line['type'] != 'message':
                continue
            ws.send(line['data'])
    except geventwebsocket.WebSocketError, e:
        logger.exception(e)
    finally:
        pub.unsubscribe()
        ws.close()

    return ''

@bp.route('/containerlog/<cid>/')
def container_log(cid):
    stderr = request.args.get('stderr', type=int, default=0)
    stdout = request.args.get('stdout', type=int, default=0)
    tail = request.args.get('tail', type=int, default=10)

    # docker client's argument
    if tail == 0:
        tail = 'all'

    ws = request.environ['wsgi.websocket']
    container = Container.get_by_container_id(cid)
    if not container:
        ws.close()
        logger.info('Container %s not found, close websocket' % cid)
        return 'websocket closed'
    try:
        client = get_docker_client(container.host.addr)
        for line in client.logs(cid, stream=True, stderr=bool(stderr), stdout=bool(stdout), tail=tail):
            ws.send(line)
    except geventwebsocket.WebSocketError, e:
        logger.exception(e)
    finally:
        try:
            ws.close()
        except:
            pass
    return ''

