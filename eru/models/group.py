#!/usr/bin/python
# coding: utf-8

import operator
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

    @classmethod
    def list_all(cls, start=0, limit=20):
        q = cls.query.offset(start)
        if limit is not None:
            q = q.limit(limit)
        return q.all()

    def list_pods(self, start=0, limit=20):
        q = self.pods
        return q[start-1:start+limit-1]

    def get_private_hosts(self, pod=None, start=0, limit=20):
        q = self.private_hosts
        if pod:
            q = q.filter_by(pod_id=pod.id).offset(start)
        if limit is not None:
            q = q.limit(limit)
        return q.all()

    def get_max_containers(self, pod, ncore, nshare):
        """
        如果你一个容器需要 ncore 个核和 nshare 份碎片
        那么这个 group 在这个 pod 能部署多少这样的容器呢?
        ncore 可为 0
        """
        # 考虑 Pod 并没有设置分享核
        if nshare and not pod.max_share_core:
            return 0

        # TODO add order by
        hosts = self.private_hosts.filter_by(pod_id=pod.id).all()
        if not hosts:
            return 0

        total = 0

        for host in hosts:
            full_cores, part_cores = host.get_free_cores()
            full_cores_num = len(full_cores)
            part_total = 0
            max_share_core = full_cores_num if pod.max_share_core == -1 else pod.max_share_core
            if nshare:
                part_total = sum(fragment.remain / nshare for fragment in part_cores)
                # 考虑1个核以下的需求
                if ncore == 0:
                    total += part_total + (max_share_core - len(part_cores)) * pod.core_share / nshare
                else:
                    # 计算使几个核为碎片核可以使整体可部署容器数最大
                    # 时间复杂度 O(N)
                    # 先得出在不增加新碎片核的情况下最大可部署数量
                    # 只要碎片核没达到最高可用碎片核之前，从独占核一个个分出去尝试看是否能组合出更多部署数量
                    max_total = max(
                            min((full_cores_num - i) / ncore, part_total + pod.core_share / nshare * i)
                            for i in range(max_share_core - len(part_cores) + 1)
                    )
                    total += max_total
            else:
                # 目标要求完全独占核
                total += full_cores_num / ncore
        return total

    def get_free_cores(self, pod, ncontainer, ncore, nshare, spec_host=None):
        """
        * 从这个group的pod的所有服务器取core的信息. 需要ncontainer个容器,
          每个需要ncore这么多独占核和nshare个比重倍率.
          尽可能先用完 host 上的核.
        * 如果spec_host设置了, 那么会在这个指定的服务器上获取core的信息
        """
        # 考虑 Pod 并没有设置分享核
        if nshare and not pod.max_share_core:
            return {}

        if spec_host is None:
            from .host import Host
            hosts = self.private_hosts.filter_by(pod_id=pod.id)\
                    .order_by(Host.count.desc()).all()
        else:
            hosts = [spec_host]
        result = {}

        for host in hosts:
            full_cores, part_cores = host.get_free_cores()
            full_result, part_result = [], []
            full_cores_num = len(full_cores)
            max_share_core = full_cores_num if pod.max_share_core == -1 else pod.max_share_core
            if nshare:
                part_result.extend(p for p in part_cores if p.remain / nshare > 0)
                # 计算碎片核能部署几个
                for fragment in part_cores:
                    part_result.extend(fragment for _ in range(fragment.remain / nshare))
                if ncore == 0:
                    # 考虑1个核以下的需求
                    for fragment in full_cores[:max_share_core - len(part_cores)]:
                        part_result.extend(fragment for _ in range(pod.core_share / nshare))
                    # 尽量使用空闲份数少的核
                    sorted(part_result, key=operator.attrgetter('remain'))
                    # ncontainer 超过 part_result 不会影响
                    if ncontainer <= len(part_result):
                        result[(host, ncontainer)] = {'part': part_result[:ncontainer]}
                        ncontainer = 0
                        break
                    result[(host, len(part_result))] = {'part': part_result}
                    ncontainer -= len(part_result)
                else:
                    # 计算使几个核为碎片核可以使整体可部署容器数最大
                    # 时间复杂度 O(N)
                    # 先得出在不增加新碎片核的情况下最大可部署数量
                    # 只要碎片核没达到最高可用碎片核之前，从独占核一个个分出去尝试看是否能组合出更多部署数量
                    can_deploy = ([], [])
                    for i in range(max_share_core - len(part_cores) + 1):
                        extend_part_cores = []
                        for core in full_cores[:i]:
                            extend_part_cores.extend(core for _ in range(pod.core_share / nshare))
                        # 算出这个组合最多部署多少个
                        can_deploy = max(
                            can_deploy, (full_cores[i:], part_cores+extend_part_cores),
                            key=lambda x: min(len(x[0])/ncore, len(x[1]))
                        )
                    full_result, part_result = can_deploy
                    count = min(len(full_result) / ncore, len(part_result))
                    # 尽量使用空闲份数少的核
                    sorted(part_result, key=operator.attrgetter('remain'))
                    if ncontainer <= count:
                        result[(host, ncontainer)] = {'full':full_result[:ncontainer*ncore],'part': part_result[:ncontainer]}
                        ncontainer = 0
                        break
                    result[(host, count)] = {'full': full_result[:count*ncore], 'part': part_result[:count]}
                    ncontainer -= count
            else:
                # 这个时候 ncore 肯定大于 0
                count = full_cores_num / ncore
                if count <= 0:
                    continue
                if ncontainer <= count:
                    result[(host, ncontainer)] = {'full': full_cores[:ncontainer*ncore]}
                    ncontainer = 0
                    break
                result[(host, count)] = {'full': full_cores[:count*ncore]}
                ncontainer -= count

        if ncontainer:
            return {}

        return result
