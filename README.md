Eru Core
=========

## Features

Core of Project Eru, for those reasons:

1. Manage container pods.
2. Control containers.
3. Update load balance configure files.

## Architecture

![Image of Architecture](http://ww3.sinaimg.cn/large/74cb2da7gw1epp7df19a8j21kw16o10v.jpg)

## Start Web

    eru

## Start async worker

    celery -A eru.app.celery worker -n 'c1' -E -P gevent

