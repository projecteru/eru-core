#!/usr/bin/python
#coding:utf-8

import sqlalchemy.exc

from eru.models import db
from eru.models.base import Base
from eru.common.settings import MAX_SHARE_CORE, CORE_SPLIT


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

    def get_max_containers(self, pod, ncore, nshare):
        """
        如果你一个容器需要 ncore 个核,
        那么这个 group 在这个 pod 能部署多少这样的容器呢?
        ncore 可为 0
        """
        hosts = self.private_hosts.filter_by(pod_id=pod.id).all()
        if not hosts:
            return 0
        total = 0
        for host in hosts:
            full_cores, part_cores = host.get_free_cores()
            full_cores_num = len(full_cores)
            full_total, part_total = 0
            if nshare:
                for p in part_cores:
                    part_total += (CORE_SPLIT - p.used) / nshare
                if ncore == 0:
                    # 考虑1个核以下的需求
                    part_total += (MAX_SHARE_CORE - len(part_cores)) * CORE_SPLIT / nshare
                    total += part_total
                else:
                    # 计算使几个核为碎片核可以使整体可部署容器数最大
                    max_total = min(full_cores_num / ncore, part_total)
                    for i in range(1, MAX_SHARE_CORE - len(part_cores) + 1):
                        full_total = (full_cores_num - i) / ncore
                        max_total = max(max_total, min(full_total, part_total + CORE_SPLIT / nshare * i))
                    total += max_total
            else:
                # 这个时候 ncore 肯定大于 0
                total += full_cores_num / ncore
        return total

    def get_free_cores(self, pod, ncontainer, ncore, nshare):
        """
        从这个 group 拥有的 pod 中取核.
        需要 ncontainer 个容器, 每个需要独立 ncore 个核，和共享的 nshare 个核，共享权重为 weight.
        尽可能先用完 host 上的核.
        """
        hosts = self.private_hosts.filter_by(pod_id=pod.id).all()
        result = {}
        for host in hosts:
            full_cores, part_cores = host.get_free_cores()
            full_result, part_result = [], []
            full_count, part_count= 0
            full_cores_num = len(full_cores)
            if nshare:
                for p in part_cores:
                    count = (CORE_SPLIT - p.used) / nshare
                    if count < 1:
                        continue
                    part_result.append(p)
                    part_count += count
                if ncore == 0:
                    # 考虑1个核以下的需求
                    part_result.extend(full_cores[:MAX_SHARE_CORE-len(part_cores)])
                    part_count += (MAX_SHARE_CORE - len(part_cores)) * CORE_SPLIT / nshare
                    #尽量使用空闲份数少的核
                    part_result.sort(cmp=lambda x, y: cmp(CORE_SPLIT-x.used, CORE_SPLIT-y.used))
                    if ncontainer <= part_count:
                        result[(host, ncontainer)] = {'part': part_result[:ncontainer]}
                        break
                    result[(host, part_count)] = {'part': part_result}
                    ncontainer = ncontainer - part_count
                else:
                    # TODO 这一坨边界情况可能有问题
                    # 计算使几个核为碎片核可以使整体可部署容器数最大
                    max_i = 0
                    max_count = min(full_cores_num / ncore, part_count)
                    for i in range(1, MAX_SHARE_CORE - len(part_cores) + 1):
                        full_count = (full_cores_num - i) / ncore
                        can_deploy = min(full_count, part_count + CORE_SPLIT / nshare * i)
                        if can_deploy > max_count:
                            max_i = i
                            max_count = can_deploy
                    if max_i:
                        full_result = full_cores[:-max_i][:max_count*ncore]
                        part_result = part_result.extend(full_cores[-max_i:])
                    else:
                        full_result = full_cores[:max_count*ncore]
                    #尽量使用空闲份数少的核
                    part_result.sort(cmp=lambda x, y: cmp(CORE_SPLIT-x.used, CORE_SPLIT-y.used))
                    if ncontainer <= max_count:
                        result[(host, ncontainer)] = {'full':full_result[:ncontainer*ncore],'part': part_result[:ncontainer]}
                        break
                    result[(host, max_count)] = {'full': full_result,'part': part_result}
                    ncontainer = ncontainer - max_count
            else:
                # 这个时候 ncore 肯定大于 0
                count = len(full_cores_num) / ncore
                if count <= 0:
                    continue
                if ncontainer <= count:
                    result[(host, ncontainer)] = {'full': full_cores[:ncontainer*ncore]}
                    break
                result[(host, count)] = {'full': full_cores[:count*ncore]}
                ncontainer = ncontainer - count
        return result

