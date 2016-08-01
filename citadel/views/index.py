# coding: utf-8

import yaml
from flask import redirect, url_for, request

from citadel.libs.view import create_page_blueprint
from citadel.config import GITLAB_URL

from citadel.action import build_image
from citadel.models.app import App
from citadel.models.gitlab import get_project_name, get_file_content


bp = create_page_blueprint('index', __name__, url_prefix='')


@bp.route('/')
def index():
    return redirect(url_for('app.index'))


@bp.route('/hook', methods=['POST'])
def hook():
    """build hook.
    目前绑定了build事件, 只有build成功了才会触发.
    有点担心这里面有些操作会慢, 不过暂时看应该没有什么问题.
    """
    data = request.get_json()
    if data['build_status'] != 'success':
        return 'build status not success: %s' % data['build_status']

    sha = data['sha']
    project_id = data['project_id']
    build_id = data['build_id']
    repo = data['repository']['git_ssh_url']

    project_name = get_project_name(repo)
    content = get_file_content(project_name, 'app.yaml', sha)
    if not content:
        return 'app.yaml not found'

    specs = yaml.load(content)
    appname = specs.get('appname', '')
    app = App.get_or_create(appname, repo)
    if not app:
        return 'error when creating app'

    artifacts = '%s/projects/%s/builds/%s/artifacts' % (GITLAB_URL, project_id, build_id)
    build_image(repo, sha, app.uid, artifacts)
    return 'ok'
