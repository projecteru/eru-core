# coding: utf-8

import time
import requests
from threading import Thread
from requests.exceptions import ConnectTimeout, ReadTimeout, ConnectionError


class ThreadWithResult(Thread):

    def __init__(self, target, args=(), kwargs=None):
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        self.rv = None
        super(ThreadWithResult, self).__init__(target=target, args=args, kwargs=kwargs)

    def run(self):
        try:
            self.rv = self.target(*self.args, **self.kwargs)
        finally:
            del self.target, self.args, self.kwargs


def _normalize_url(url):
    if not url.startswith('http://'):
        url = 'http://%s' % url
    return url


def _check_one_url(url):
    total = 0
    while total < 10:
        try:
            requests.get(_normalize_url(url), timeout=0.5)
        except (ConnectTimeout, ReadTimeout, ConnectionError):
            pass
        else:
            return True
        total += 1
        time.sleep(1)

    return False


def wait_health_check(urls):
    threads = [ThreadWithResult(target=_check_one_url, args=(url,),) for url in urls]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return all([t.rv for t in threads])
