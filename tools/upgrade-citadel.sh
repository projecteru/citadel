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
  ssh c1-eru-1 -t "sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git reset --hard $remote/$branch"
  ssh c1-eru-1 -t "sudo pip install -U git+http://gitlab.ricebook.net/platform/erulb3.git#egg=erulb-py -i https://pypi.doubanio.com/simple/"
  ssh c1-eru-1 -t 'sudo systemctl restart citadel citadel-worker watch-etcd'
elif [ $deploy_mode == "devel" ]
then
  ssh c2-eru-1 -t 'sudo git --work-tree=/opt/citadel-devel --git-dir=/opt/citadel-devel/.git fetch --all --prune'
  ssh c2-eru-1 -t "sudo git --work-tree=/opt/citadel-devel --git-dir=/opt/citadel-devel/.git reset --hard $remote/$branch"
elif [ $deploy_mode == "prod" ]
then
  cat > ~/.corecli.json << EOF
{"sso_url": "http://sso.ricebook.net", "citadel_url": "http://citadel.ricebook.net", "auth_token": "***REMOVED***", "mimiron_url": "", "username": "liuyifu"}
EOF
  ssh c2-eru-1 -t 'sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git fetch --all --prune'
  ssh c2-eru-1 -t "sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git reset --hard $remote/$branch"
  ssh c2-eru-1 -t "sudo pip install -U git+http://gitlab.ricebook.net/platform/erulb3.git#egg=erulb-py -i https://pypi.doubanio.com/simple/"
  ssh c2-eru-1 -t 'sudo systemctl restart citadel citadel-worker watch-etcd'

  # update zone c1 watch-etcd.service
  ssh c1-eru-1 -t 'sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git fetch --all --prune'
  ssh c1-eru-1 -t "sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git reset --hard $remote/$branch"
  ssh c1-eru-1 -t "sudo pip install -U git+http://gitlab.ricebook.net/platform/erulb3.git#egg=erulb-py -i https://pypi.doubanio.com/simple/"
  ssh c1-eru-1 -t 'sudo systemctl restart watch-etcd'
else
  exit 127
fi
