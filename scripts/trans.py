#!/usr/bin/python
#coding:utf-8

import sys
import json
import redis

v = json.dumps({})

def main():
    r = redis.StrictRedis(host=sys.argv[1])
    for key in r.keys('eru:agent:*:containers'):
        new_key = '%s:meta' % key
        for cid in r.smembers(key):
            r.hset(new_key, cid, v)

if __name__=='__main__':
    main()

