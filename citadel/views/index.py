# coding: utf-8
import yaml
from flask import redirect, url_for, request

from citadel import flask_app
from citadel.action import build_image, ActionError
from citadel.config import GITLAB_API_URL
from citadel.libs.utils import logger
from citadel.libs.view import create_page_blueprint
from citadel.models.app import App, Release
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
    if not data:
        logger.info('No data provided')
        return 'No data provided'

    try:
        build_status = data['build_status']
        sha = data['sha']
        project_id = data['project_id']
        build_id = data['build_id']
        repo = data['repository']['git_ssh_url']
    except KeyError as e:
        logger.error('key not found in hook: %s', e.message)
        return 'Bad format of JSON data'

    if build_status != 'success':
        logger.error('build status not success: %s', build_status)
        return 'build status not success: %s' % data['build_status']

    project_name = get_project_name(repo)
    specs_text = get_file_content(project_name, 'app.yaml', sha)
    if not specs_text:
        return 'app.yaml not found'

    specs = yaml.load(specs_text)
    appname = specs.get('appname', '')
    app = App.get_or_create(appname, repo)
    if not app:
        return 'error when creating app'

    release = Release.create(app, sha)
    if not release:
        return 'error when creating release'

    artifacts = '%s/projects/%s/builds/%s/artifacts' % (GITLAB_API_URL, project_id, build_id)
    try:
        build_image(repo, sha, app.uid, artifacts)
    except ActionError as e:
        logger.error('error when build image: %s', e.message)
    return 'ok'


flask_app.register_blueprint(bp)
