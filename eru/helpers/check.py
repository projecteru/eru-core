# coding: utf-8

import time
import requests
from requests.exceptions import ConnectTimeout, ReadTimeout


def _normalize_url(url):
    if not url.startswith('http://'):
        url = 'http://%s' % url
    return url


def wait_health_check(urls):
    total = len(urls)
    while total:
        for url in urls:
            try:
                requests.get(_normalize_url(url), timeout=0.5)
                total -= 1
            except (ConnectTimeout, ReadTimeout):
                pass
        if total:
            time.sleep(1)
    # 给个返回值是怕有些用coroutine的会switch走
    return True
