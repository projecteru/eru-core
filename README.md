Eru Core
=========

[![Build Status](https://travis-ci.org/HunanTV/eru-core.svg?branch=master)](https://travis-ci.org/HunanTV/eru-core)

## Requirements

    libgit2

## Start Service

    eru

## Start Worker

    celery -A eru.app.celery worker -n 'c1' -E -P gevent

