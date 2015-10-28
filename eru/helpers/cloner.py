# coding: utf-8

import pygit2

from eru.config import GIT_KEY_PUB, GIT_KEY_PRI, GIT_KEY_USER, GIT_KEY_ENCRYPT
from eru.config import GIT_USERNAME, GIT_PASSWORD


class CloneError(Exception):
    pass


def _get_credit():
    if (GIT_KEY_PUB and GIT_KEY_PRI and GIT_KEY_USER):
        return 'ssh', pygit2.credentials.Keypair(GIT_KEY_USER,
                GIT_KEY_PUB, GIT_KEY_PRI, GIT_KEY_ENCRYPT)
    if (GIT_USERNAME and GIT_PASSWORD):
        return 'http', pygit2.credentials.UserPass(GIT_USERNAME, GIT_PASSWORD)
    return '', None


def clone_code(repo_url, clone_path, revision, branch=None):
    """branch 为 None, 默认用远端的 default branch"""
    type, cred = _get_credit()
    if type == 'ssh' and repo_url.startswith('git'):
        raise CloneError('Use ssh while repo url is %s' % repo_url)

    repo = pygit2.clone_repository(repo_url, clone_path,
            bare=False, checkout_branch=branch, credentials=cred)
    repo.checkout('HEAD')
    obj = repo.revparse_single(revision)
    repo.checkout_tree(obj.tree)
