# coding: utf-8

import redis
import random
import string
import argparse

rds = None

def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument(dest='host_name', help='host name, e.g. kili1')
    parser.add_argument(dest='redis_host', help='redis host, e.g. localhost', default='127.0.0.1')
    parser.add_argument(dest='redis_port', help='redis port, e.g. 6379', default=6379, type=int)
    return parser.parse_args()

def init_redis(redis_host, redis_port):
    global rds
    if rds is None:
        rds = redis.Redis(redis_host, redis_port)

def agent(host_name):
    pub = rds.pubsub()
    pub.subscribe('eru:agent:%s:vlan' % host_name)
    for m in pub.listen():
        if m['type'] != 'message':
            continue
        p = m['data'].split('|')
        print p
        task_id, container_id, ident = p[0], p[1], p[2]
        feed_key = 'eru:agent:%s:feedback' % task_id
        for content in p[3:]:
            add_vlan(feed_key, content, ident, container_id)

def add_vlan(feed_key, content, ident, container_id):
    print content
    seq, ip = content.split(':')
    veth_name = 'veth.%s.' % seq + ''.join(random.sample(string.ascii_letters, 5))
    rds.lpush(feed_key, '|'.join(['1', container_id, veth_name, ip]))

if __name__ == '__main__':
    p = parse()
    init_redis(p.redis_host, p.redis_port)
    agent(p.host_name)
