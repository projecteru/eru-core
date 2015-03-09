# coding: utf-8

from flask import Blueprint, request

from eru.models import Task
from eru.common.clients import rds

bp = Blueprint('websockets', __name__, url_prefix='/websockets')

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
                if line['data'] == 'ERU_KILL_PUB':
                    pub.unsubscribe()
                    break
                if line['type'] != 'message':
                    continue
                ws.send(line['data'])
        else:
            for line in task.log():
                ws.send(line)
    except:
        pass
    finally:
        ws.close()

    return 'websocket closed'

