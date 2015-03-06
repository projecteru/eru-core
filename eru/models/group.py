#!/usr/bin/python
#coding:utf-8

import sqlalchemy.exc

from eru.models import db
from eru.models.base import Base


class GroupPod(db.Model):

    group_id = db.Column(db.ForeignKey('group.id'), primary_key=True)
    pod_id = db.Column(db.ForeignKey('pod.id'), primary_key=True)


class Group(Base):
    __tablename__ = 'group'

    name = db.Column(db.CHAR(30), nullable=False, unique=True)
    description = db.Column(db.Text)

    pods = db.relationship('Pod', secondary=GroupPod.__table__)
    private_hosts = db.relationship('Host', backref='group', lazy='dynamic')
    apps = db.relationship('App', backref='group', lazy='dynamic')

    def __init__(self, name, description):
        self.name = name
        self.description = description

    @classmethod
    def create(cls, name, description=''):
        try:
            group = cls(name, description)
            db.session.add(group)
            db.session.commit()
            return group
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter(cls.name == name).first()

    def get_max_containers(self, pod, cores_per_container):
        """
        如果你一个容器需要 cores_per_container 个核,
        那么这个 group 在这个 pod 能部署多少这样的容器呢?
        """
        hosts = self.private_hosts.filter_by(pod_id=pod.id).all()
        if not hosts:
            return 0
        total = 0
        for host in hosts:
            cores = len(host.get_free_cores())
            total += cores / cores_per_container
        return total

    def get_free_cores(self, pod, ncontainer, cores_per_container):
        """
        从这个 group 拥有的 pod 中取核.
        需要 ncontainer 个容器, 每个需要 cores_per_container 个核.
        尽可能先用完 host 上的核.
        """
        hosts = self.private_hosts.filter_by(pod_id=pod.id).all()
        result = {}
        for host in hosts:
            cores = host.get_free_cores()
            count = len(cores) / cores_per_container
            if count <= 0:
                continue
            if ncontainer <= count:
                result[(host, ncontainer)] = cores[:ncontainer*cores_per_container]
                break
            result[(host, count)] = cores[:count*cores_per_container]
            ncontainer = ncontainer - count
        return result

