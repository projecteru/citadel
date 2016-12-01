#!/bin/sh


if [ $1 == "test" ]; then
  cat > ~/.corecli.json << EOF
{"sso_url": "http://sso.ricebook.net", "citadel_url": "http://citadel.test.ricebook.net", "auth_token": "***REMOVED***", "mimiron_url": "", "username": "liuyifu"}
EOF
  ssh c1-eru-1.ricebook.link -t 'sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git fetch --all --prune'
  ssh c1-eru-1.ricebook.link -t 'sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git reset --hard origin/master'
  ssh c1-eru-1.ricebook.link -t 'sudo systemctl restart citadel'
  ssh c1-eru-1.ricebook.link -t 'sudo systemctl restart citadel-worker'
else
  cat > ~/.corecli.json << EOF
{"sso_url": "http://sso.ricebook.net", "citadel_url": "http://citadel.ricebook.net", "auth_token": "***REMOVED***", "mimiron_url": "", "username": "liuyifu"}
EOF
  ssh c2-eru-1.ricebook.link -t 'sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git fetch --all --prune'
  ssh c2-eru-1.ricebook.link -t 'sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git reset --hard origin/master'
  ssh c2-eru-1.ricebook.link -t 'sudo systemctl restart citadel'
  ssh c2-eru-1.ricebook.link -t 'sudo systemctl restart citadel-worker'
fi
