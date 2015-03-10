# coding: utf-8

import logging
import geventwebsocket
from flask import Blueprint, request

from eru.models import Task
from eru.common import code
from eru.common.clients import rds

bp = Blueprint('websockets', __name__, url_prefix='/websockets')
logger = logging.getLogger(__name__)

def _get_websocket_from_request(request):
    return request.environ['wsgi.websocket']

@bp.route('/tasklog/<int:task_id>/')
def task_log(task_id):
    ws = _get_websocket_from_request(request)

    task = Task.get(task_id)
    if not task:
        ws.close()
        return 'websocket closed'

    try:

        if not task.finished:
            for line in task.log():
                ws.send(line)

            pub = rds.pubsub()
            pub.subscribe(task.publish_key)
            for line in pub.listen():
                if line['data'] == code.PUB_END_MESSAGE:
                    pub.unsubscribe()
                    break
                if line['type'] != 'message':
                    continue
                ws.send(line['data'])
        else:
            for line in task.log():
                ws.send(line)
    except geventwebsocket.WebSocketError as e:
        logger.exception(e)
    finally:
        ws.close()

    return 'websocket closed'

