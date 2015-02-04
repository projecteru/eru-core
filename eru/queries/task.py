#!/usr/bin/python
#coding:utf-8

import logging
import sqlalchemy.exc

from eru.models import db, Task

def create_task(typ, application, version, host):
    try:
        task = Task(typ)
        application.tasks.append(task)
        version.tasks.append(task)
        host.tasks.append(task)
        db.session.add(task)
        db.session.add(application)
        db.session.add(version)
        db.session.add(host)
        db.session.commit()
        return task
    except sqlalchemy.exc.IntegrityError, e:
        db.session.rollback()
        logging.exception(e)
        return False

def done(task, result):
    task.set_result(result)
    task.finish()
    db.session.add(task)
    db.session.commit()

