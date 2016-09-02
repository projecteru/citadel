# coding: utf-8

from __future__ import absolute_import

import re
from base64 import b64decode
from urlparse import urlparse

from citadel.ext import gitlab
from citadel.libs.utils import handle_gitlab_exception
from citadel.libs.cache import cache, ONE_DAY


_PROJECT_NAME_REGEX = re.compile(r'^(\w+)@([^:]+):(.+)\.git$')


def get_project_name(repo):
    r = _PROJECT_NAME_REGEX.match(repo)
    if r:
        return r.group(3)

    u = urlparse(repo)
    return u.path[1:-4]


@cache('citadel:filecontent:{project_name}:{file_path}:{ref}', ttl=ONE_DAY)
def get_file_content(project_name, file_path, ref):

    @handle_gitlab_exception(default=None)
    def _get_file_content(project_name, file_path, ref):
        p = gitlab.projects.get(project_name)
        f = p.files.get(file_path=file_path, ref=ref)
        return b64decode(f.content)

    return _get_file_content(project_name, file_path, ref)


@handle_gitlab_exception(default=None)
def get_commit(project_name, ref):
    p = gitlab.projects.get(project_name)
    return p.commits.get(ref)


@handle_gitlab_exception(default=None)
def get_project(project_name):
    return gitlab.projects.get(project_name)
