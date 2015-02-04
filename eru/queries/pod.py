#!/usr/bin/python
#coding:utf-8

import logging
import sqlalchemy.exc
from eru.models import db, Pod

logger = logging.getLogger(__name__)

def create_pod(name, description=""):
    pod = Pod(name, description)
    try:
        db.session.add(pod)
        db.session.commit()
        return pod
    except sqlalchemy.exc.IntegrityError, e:
        db.session.rollback()
        logger.exception(e)
        return False

