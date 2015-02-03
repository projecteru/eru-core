#!/usr/bin/python
#coding:utf-8

import logging
import sqlalchemy.exc
from eru.models import db, Pods

logger = logging.getLogger(__name__)

def create_pod(name, description=""):
    pod = Pods(name, description)
    try:
        db.session.add(pod)
        db.session.commit()
        return True
    except sqlalchemy.exc.IntegrityError, e:
        db.session.rollback()
        logger.exception(e)
        return False

