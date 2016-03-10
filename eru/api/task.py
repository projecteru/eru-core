# coding: utf-8
import json

from flask import abort

from .bp import create_api_blueprint
from eru.models import Task
from eru.redis_client import rds


bp = create_api_blueprint('task', __name__, url_prefix='/api/task')


@bp.route('/<task_id>/')
def get_task(task_id):
    task = Task.get(task_id)
    if not task:
        abort(404, 'Task %s not found' % task_id)
    return task


@bp.route('/<task_id>/log/')
def task_log(task_id):
    task = Task.get(task_id)
    if not task:
        abort(404, 'Task %s not found' % task_id)

    return [json.loads(l) for l in rds.lrange(task.log_key, 0, -1)]
