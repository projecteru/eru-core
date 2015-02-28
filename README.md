Eru Core
=========

## Features

Core of Project Eru, for those reasons:

1. Manage container pods.
2. Control containers.
3. Update load balance configure files.

## Architecture

![Image of Architecture](http://img3.douban.com/view/status/raw/public/2dc6eda24caf8e4.jpg)

## Start Web

    `eru`

## Start async worker

    `celery -A eru.app.celery worker -n 'c1' -E -P gevent`

