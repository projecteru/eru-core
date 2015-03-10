# coding: utf-8

import logging
import geventwebsocket
from flask import Blueprint, request

from eru.models import Task
from eru.common import code
from eru.common.clients import rds

bp = Blueprint('websockets', __name__, url_prefix='/websockets')
logger = logging.getLogger(__name__)

@bp.route('/tasklog/<int:task_id>/')
def task_log(task_id):
    ws = request.environ['wsgi.websocket']

    task = Task.get(task_id)
    if not task:
        ws.close()
        return 'websocket closed'

    try:
        pub = rds.pubsub()
        pub.subscribe(task.publish_key)

        for line in task.log():
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

