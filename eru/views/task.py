# coding: utf-8

from flask import Blueprint

from eru.models import Task
from eru.common import code
from eru.utils.views import jsonify, EruAbortException


bp = Blueprint('task', __name__, url_prefix='/api/task')


@bp.route('/<task_id>/')
@jsonify()
def get_task(task_id):
    task = Task.get(task_id)
    if not task:
        raise EruAbortException(code.HTTP_NOT_FOUND, 'Task %s not found' % task_id)
    return task


@bp.errorhandler(EruAbortException)
@jsonify()
def eru_abort_handler(exception):
    return {'r': 1, 'msg': exception.msg, 'status_code': exception.code}

