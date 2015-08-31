# coding: utf-8

import uuid
import random
import hashlib

from werkzeug.security import gen_salt

def random_ipv4():
    return '.'.join(str(random.randint(0, 255)) for _ in range(4))

def random_string(prefix='', random_size=4):
    return prefix + gen_salt(random_size)

def random_uuid():
    return str(uuid.uuid4())

def random_sha1():
    return hashlib.sha1(random_string(random_size=8)).hexdigest()
