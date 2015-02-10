#!/usr/bin/python
#coding:utf-8

import sqlalchemy.exc

from eru.models import db, Base


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

    def get_max_containers(self, per_core):
        """
        如果你一个容器需要 per_core 个核,
        那么这个 group 能部署多少这样的容器呢?
        """
        hosts = self.private_hosts.all()
        if not hosts:
            return 0
        total = 0
        for host in hosts:
            cores = len(host.get_free_cores())
            total += cores / per_core
        return total

    def get_free_cores(self, pod, ncontainer, per_core):
        hosts = self.private_hosts.filter_by(name=pod.name).all()
        result = {}
        for host in hosts:
            cores = host.get_free_cores()
            count = len(cores) / per_core
            if count <= 0:
                continue
            if ncontainer <= count:
                return {(host, count): cores[:ncontainer*per_core]}
            result[(host, count)] = cores
            ncontainer = ncontainer - count
        return result

