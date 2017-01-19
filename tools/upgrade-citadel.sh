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
  echo "corecli config has been set to citadel.test.ricebook.net"
  ssh c1-eru-2 << EOF
  sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git fetch --all --prune
  sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git reset --hard $remote/$branch
  sudo pip install -U git+http://gitlab.ricebook.net/platform/erulb3.git#egg=erulb-py -i https://pypi.doubanio.com/simple/
  sudo pip install -e git+http://gitlab.ricebook.net/platform/mapi.git#egg=mapi -i https://pypi.doubanio.com/simple/
  sudo systemctl restart citadel citadel-worker watch-etcd
EOF
elif [ $deploy_mode == "devel" ]
then
  port=5003
  ssh c2-eru-1 -t << EOF
  sudo fuser -k $port/tcp
  sudo git --work-tree=/opt/citadel-devel --git-dir=/opt/citadel-devel/.git fetch --all --prune
  sudo git --work-tree=/opt/citadel-devel --git-dir=/opt/citadel-devel/.git reset --hard $remote/$branch
  gunicorn --chdir /opt/citadel citadel.app:app --bind 0.0.0.0:$port --timeout 1200
EOF
elif [ $deploy_mode == "prod" ]
then
  cat > ~/.corecli.json << EOF
{"sso_url": "http://sso.ricebook.net", "citadel_url": "http://citadel.ricebook.net", "auth_token": "***REMOVED***", "mimiron_url": "", "username": "liuyifu"}
EOF
  echo "corecli config has been set to citadel.ricebook.net"
  ssh c2-eru-1 << EOF
  sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git fetch --all --prune
  sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git reset --hard $remote/$branch
  sudo pip install -U git+http://gitlab.ricebook.net/platform/erulb3.git#egg=erulb-py -i https://pypi.doubanio.com/simple/
  sudo pip install -e git+http://gitlab.ricebook.net/platform/mapi.git#egg=mapi -i https://pypi.doubanio.com/simple/
  sudo systemctl restart citadel citadel-worker watch-etcd

EOF
  # update zone c1 watch-etcd.service
  ssh c1-eru-1 << EOF
  sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git fetch --all --prune
  sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git reset --hard $remote/$branch
  sudo pip install -U git+http://gitlab.ricebook.net/platform/erulb3.git#egg=erulb-py -i https://pypi.doubanio.com/simple/
  sudo pip install -e git+http://gitlab.ricebook.net/platform/mapi.git#egg=mapi -i https://pypi.doubanio.com/simple/
  sudo systemctl restart watch-etcd
EOF
else
  exit 127
fi
