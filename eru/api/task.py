# coding: utf-8

from flask import Blueprint

from eru import consts
from eru.models import Task
from eru.utils.decorator import jsonify
from eru.utils.exception import EruAbortException

bp = Blueprint('task', __name__, url_prefix='/api/task')

@bp.route('/<task_id>/')
@jsonify
def get_task(task_id):
    task = Task.get(task_id)
    if not task:
        raise EruAbortException(consts.HTTP_NOT_FOUND, 'Task %s not found' % task_id)
    return task
