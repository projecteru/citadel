# coding: utf-8

from __future__ import absolute_import

from base64 import b64decode
from gitlab import GitlabError
from functools import partial
from urlparse import urlparse

from citadel.ext import gitlab
from citadel.libs.utils import handle_exception


handle_gitlab_exception = partial(handle_exception, (GitlabError,))


def get_project_name(repo):
    if repo.startswith('git@'):
        return repo.split(':', 1)[1][:-4]

    u = urlparse(repo)
    return u.path[1:-4]


@handle_gitlab_exception(default='')
def get_file_content(project_name, file_path, ref):
    p = gitlab.projects.get(project_name)
    f = p.files.get(file_path=file_path, ref=ref)
    return b64decode(f.content)


@handle_gitlab_exception(default=None)
def get_commit(project_name, ref):
    p = gitlab.projects.get(project_name)
    return p.commits.get(ref)


@handle_gitlab_exception(default=None)
def get_project(project_name):
    return gitlab.projects.get(project_name)
