# coding: utf-8

from urlparse import urlparse

def is_strict_url(u):
    try:
        p = urlparse(u)
        return p and p.scheme and p.netloc
    except:
        return False
