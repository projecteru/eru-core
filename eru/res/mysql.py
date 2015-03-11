#!/usr/bin/python
#coding:utf-8

import MySQLdb

from eru.res import Base
from eru.common import settings

from res.ext.mysql import create_mysql


class MySQL(Base):

    conn = MySQLdb.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        passwd=settings.MYSQL_PASSWORD,
    )

    @classmethod
    def alloc(cls, dbname, username, pass_len):
        return create_mysql(cls.conn, dbname, username, pass_len)


    #TODO clean data
    @classmethod
    def free(cls):
        pass

