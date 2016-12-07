#!/bin/sh


set -e
deploy_mode=${1-test}
remote=${2-origin}
branch=${3-master}

if [ $deploy_mode == "test" ]
then
  cat > ~/.corecli.json << EOF
{"sso_url": "http://sso.ricebook.net", "citadel_url": "http://citadel.test.ricebook.net", "auth_token": "***REMOVED***", "mimiron_url": "", "username": "liuyifu"}
EOF
  ssh c1-eru-1 -t 'sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git fetch --all --prune'
  ssh c1-eru-1 -t "sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git checkout $remote/$branch"
  ssh c1-eru-1 -t "sudo pip install -U git+http://gitlab.ricebook.net/platform/erulb3.git#egg=erulb-py -i https://pypi.doubanio.com/simple/"
  ssh c1-eru-1 -t 'sudo systemctl restart citadel citadel-worker'
elif [ $deploy_mode == "prod" ]
then
  cat > ~/.corecli.json << EOF
{"sso_url": "http://sso.ricebook.net", "citadel_url": "http://citadel.ricebook.net", "auth_token": "***REMOVED***", "mimiron_url": "", "username": "liuyifu"}
EOF
  ssh c2-eru-1 -t 'sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git fetch --all --prune'
  ssh c2-eru-1 -t "sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git checkout $remote/$branch"
  ssh c1-eru-1 -t "sudo pip install -U git+http://gitlab.ricebook.net/platform/erulb3.git#egg=erulb-py -i https://pypi.doubanio.com/simple/"
  ssh c2-eru-1 -t 'sudo systemctl restart citadel citadel-worker'
else
  exit 127
fi
