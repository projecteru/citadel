# coding: utf-8

import json
import yaml
from flask import abort, request, Response

from citadel.ext import core
from citadel.libs.json import JSONEncoder
from citadel.libs.view import create_api_blueprint
from citadel.libs.datastructure import AbortDict

from citadel.models.app import App
from citadel.models.gitlab import get_project_name, get_file_content


# 把action都挂在/api/:version/下, 不再加前缀
# 也不需要他帮忙自动转JSON了
bp = create_api_blueprint('action', __name__, jsonize=False)


@bp.route('/build', methods=['POST'])
def build():
    """
    可以这么玩玩:
    $ http --stream POST localhost:5000/api/v1/build repo=git@gitlab.ricebook.net:tonic/ci-test.git sha=1d74377e99dcfb3fd892f9eaeab91e1e229179ba uid=4401
    """
    data = AbortDict(request.get_json())

    repo = data['repo']
    sha = data['sha']
    artifact = data.get('artifact', '')

    project_name = get_project_name(repo)
    content = get_file_content(project_name, 'app.yaml', sha)
    if not content:
        abort(400, 'repo %s does not have app.yaml in root directory' % repo)

    specs = yaml.load(content)
    if 'appname' not in specs:
        abort(400, 'repo %s does not specify appname in app.yaml' % repo)

    app = App.get_by_name(specs['appname'])
    if not app:
        abort(400, 'repo %s does not have the right appname in app.yaml' % repo)

    uid = data.get('uid', None) or app.id

    def stream():
        for m in core.build_image(repo, sha, str(uid), artifact):
            yield json.dumps(m, cls=JSONEncoder) + '\n'

    return Response(stream(), mimetype='application/json')
