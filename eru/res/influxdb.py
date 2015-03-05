#!/usr/bin/python
#coding:utf-8

from eru.res import Base
from eru.common import settings

from res.ext.common import get_influxdb_client
from res.ext.influxdb import create_influxdb

class InfluxDB(Base):

    client = get_influxdb_client(
        host=settings.INFLUXDB_HOST,
        port=settings.INFLUXDB_PORT,
        username=settings.INFLUXDB_USERNAME,
        password=settings.INFLUXDB_PASSWORD,
    )

    @classmethod
    def alloc(cls, dbname, username, pass_len, admin=False):
        return create_influxdb(cls.client, dbname, username, pass_len, admin)

    #TODO clean data
    @classmethod
    def free(cls):
        pass

