# coding: utf-8

from flask import abort

from eru.models import Task

from .bp import create_api_blueprint

bp = create_api_blueprint('task', __name__, url_prefix='/api/task')

@bp.route('/<task_id>/')
def get_task(task_id):
    task = Task.get(task_id)
    if not task:
        abort(404, 'Task %s not found' % task_id)
    return task
