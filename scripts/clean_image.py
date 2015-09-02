# coding: utf-8

from functools import wraps

from eru.app import create_app_with_celery
from eru.models import Host
from eru.config import DOCKER_REGISTRY
from eru.clients import get_docker_client


def with_app_context(f):
    @wraps(f)
    def _(*args, **kwargs):
        app, _ = create_app_with_celery()
        with app.app_context():
            return f(*args, **kwargs)
    return _


def need_to_delete_container(image, name):
    ps = name.split('_')
    return not (image.startswith(DOCKER_REGISTRY) and len(ps) == 3)


@with_app_context
def clean_image():
    for host in Host.query.all():
        client = get_docker_client(host.addr)
        if not client:
            continue

        try:
            client.ping()
        except:
            print 'client not connected, skipped.'
            continue

        for c in client.containers(all=True):
            if need_to_delete_container(c['Image'], c['Names'][0]):
                try:
                    client.remove_container(c['Id'])
                    print 'container %s cleaned.' % c['Names'][0]
                except:
                    print 'container %s still running.' % c['Names'][0]

        for i in client.images():
            try:
                client.remove_image(i['Id'])
                print 'image %s cleaned.' % i['RepoTags'][0]
            except:
                print 'conflict, image %s is still being used.' % i['RepoTags'][0]

        print 'host %s cleaned.' % host.ip


if __name__ == '__main__':
    clean_image()
