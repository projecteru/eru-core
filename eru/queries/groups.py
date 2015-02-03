#!/usr/bin/python
#coding:utf-8

import logging
import sqlalchemy.exc
from eru.models import db, Groups, Pods

logger = logging.getLogger(__name__)

def create_group(name, description=""):
    group = Groups(name, description)
    try:
        db.session.add(group)
        db.session.commit()
        return True
    except sqlalchemy.exc.IntegrityError, e:
        db.session.rollback()
        logger.exception(e)
        return False

def assign_pod(group_name, pod_name):
    group = Groups.query.filter_by(name=group_name).first()
    pod = Pods.query.filter_by(name=pod_name).first()
    if not group or not pod:
        return False
    group.pods.append(pod)
    db.session.add(group)
    db.session.commit()
    return True

