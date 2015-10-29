# coding: utf-8

import time
import requests
from threading import Thread
from requests.exceptions import ConnectTimeout, ReadTimeout, ConnectionError


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
            break
        total += 1
        time.sleep(1)


def wait_health_check(urls):
    threads = [Thread(target=_check_one_url, args=(url,),) for url in urls]
    [t.start() for t in threads]
    [t.join() for t in threads]
