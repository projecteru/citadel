# coding: utf-8

from __future__ import absolute_import

import re
from operator import attrgetter
from base64 import b64decode
from urlparse import urlparse

from citadel.ext import gitlab
from citadel.config import GITLAB_API_URL
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


def get_build_artifact(project_name, ref, build_id):
    """
    尝试通过build_id和ref去获取一次build的artifact.
    这次build可能没有, 那么需要找到最近一次有artifact的build.
    TODO: 现在这里是直接用的commit的build, 实际上不需要commit, 一次build可以拿到pipeline, 通过pipeline找artifact更靠谱.
    """
    if not build_id or not build_id.isdigit():
        return ''

    build_id = int(build_id)
    project = get_project(project_name)
    if not project:
        return ''

    commit = get_commit(project_name, ref)
    if not commit:
        return ''

    build = next((b for b in sorted(commit.builds(), key=attrgetter('id')) if getattr(b, 'artifacts_file', None) and b.id < build_id), None)
    if not build:
        return ''

    return '%s/projects/%s/builds/%s/artifacts' % (GITLAB_API_URL, project.id, build.id)
