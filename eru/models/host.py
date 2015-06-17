# coding:utf-8

import sqlalchemy.exc

from eru.models import db
from eru.models.base import Base
from eru.clients import rds

_pipeline = rds.pipeline()

class Core(object):

    def __init__(self, label, host_id, remain=10):
        self.label = label
        self.host_id = host_id
        self.remain = remain

    def __repr__(self):
        return '<Core(label={0}, host_id={1}, remain={2})>'.format(
            self.label, self.host_id, self.remain)

    def is_free(self):
        return self.remain == 0

def _create_cores_on_host(host, count):
    data = {str(i): host.pod.core_share for i in xrange(count)}
    rds.zadd(host._cores_key, **data)

class Host(Base):
    __tablename__ = 'host'

    addr = db.Column(db.CHAR(30), nullable=False, unique=True)
    name = db.Column(db.CHAR(30), nullable=False)
    uid = db.Column(db.CHAR(60), nullable=False)
    ncore= db.Column(db.Integer, nullable=False, default=0)
    mem = db.Column(db.BigInteger, nullable=False, default=0)
    # 现在这个count是指free的core数
    count = db.Column(db.Integer, nullable=False, default=0)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    pod_id = db.Column(db.Integer, db.ForeignKey('pod.id'))
    is_alive = db.Column(db.Boolean, default=True)

    tasks = db.relationship('Task', backref='host', lazy='dynamic')
    containers = db.relationship('Container', backref='host', lazy='dynamic')

    def __init__(self, addr, name, uid, ncore, mem, pod_id, count):
        self.addr = addr
        self.name = name
        self.uid = uid
        self.ncore = ncore
        self.mem = mem
        self.pod_id = pod_id
        self.count = count

    @classmethod
    def create(cls, pod, addr, name, uid, ncore, mem):
        """创建必须挂在一个 pod 下面"""
        if not pod:
            return None
        try:
            host = cls(addr, name, uid, ncore, mem, pod.id, ncore)
            db.session.add(host)
            db.session.commit()
            _create_cores_on_host(host, ncore)
            return host
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            return None

    @classmethod
    def get_by_addr(cls, addr):
        return cls.query.filter(cls.addr == addr).first()

    @classmethod
    def get_by_name(cls, name):
        return cls.query.filter(cls.name == name).first()

    @property
    def ip(self):
        return self.addr.split(':', 1)[0]

    @property
    def _cores_key(self):
        return 'eru:host:%s:cores' % self.id

    @property
    def cores(self):
        r = rds.zrange(self._cores_key, 0, -1, withscores=True, score_cast_func=int)
        return [Core(name, self.id, value) for name, value in r]

    def list_containers(self, start=0, limit=20):
        q = self.containers.offset(start)
        if limit is not None:
            q = q.limit(limit)
        return q.all()

    def get_free_cores(self):
        """取可用的core, 返回一个完全可用列表, 以及部分可用列表"""
        slice_count = self.pod.core_share
        # 条件查询 O(log(N)+M) 排除已经用完的 Core
        r = rds.zrangebyscore(self._cores_key, '(0', slice_count, withscores=True, score_cast_func=int)
        full = []
        fragment = []
        for name, value in r:
            c = Core(name, self.id, value)
            if value == slice_count:
                full.append(c)
            elif 0 < value < slice_count:
                fragment.append(c)
        return full, fragment

    def get_filtered_containers(self, version=None, entrypoint=None, app=None, start=0, limit=20):
        q = self.containers
        if version is not None:
            q = q.filter_by(version_id=version.id)
        if entrypoint is not None:
            q = q.filter_by(entrypoint=entrypoint)
        if app is not None:
            q = q.filter_by(app_id=app.id)
        return q.offset(start).limit(limit).all()

    def get_containers_by_version(self, version):
        return self.containers.filter_by(version_id=version.id).all()

    def get_containers_by_app(self, app):
        return self.containers.filter_by(app_id=app.id).all()

    def assigned_to_group(self, group):
        """分配给 group, 那么这个 host 被标记为这个 group 私有"""
        if not group:
            return False
        group.private_hosts.append(self)
        db.session.add(group)
        db.session.commit()
        return True

    def occupy_cores(self, cores, nshare):
        slice_count = self.pod.core_share
        for core in cores.get('full', []):
            _pipeline.zincrby(self._cores_key, core.label, -slice_count)
        for core in cores.get('part', []):
            _pipeline.zincrby(self._cores_key, core.label, -nshare)
        _pipeline.execute()

    def release_cores(self, cores, nshare):
        slice_count = self.pod.core_share
        for core in cores.get('full', []):
            _pipeline.zincrby(self._cores_key, core.label, slice_count)
        for core in cores.get('part', []):
            _pipeline.zincrby(self._cores_key, core.label, nshare)
        _pipeline.execute()

    def kill(self):
        """一个host上不会太多container"""
        self.is_alive = False
        for c in self.containers.all():
            c.is_alive = 0
            db.session.add(c)
        db.session.add(self)
        db.session.commit()

    def cure(self):
        """一个host上不会太多container"""
        self.is_alive = True
        for c in self.containers.all():
            c.is_alive = 1
            db.session.add(c)
        db.session.add(self)
        db.session.commit()
