#!/bin/sh

celery -A eru.app.celery worker
