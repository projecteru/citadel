#!/bin/sh


if [ $1 == "test" ]; then
  cat > ~/.corecli.json << EOF
{"sso_url": "http://sso.ricebook.net", "citadel_url": "http://citadel.test.ricebook.net", "auth_token": "***REMOVED***", "mimiron_url": "", "username": "liuyifu"}
EOF
  ssh binge -t 'sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git pull'
  ssh binge -t 'sudo systemctl restart citadel'
else
  cat > ~/.corecli.json << EOF
{"sso_url": "http://sso.ricebook.net", "citadel_url": "http://citadel.ricebook.net", "auth_token": "***REMOVED***", "mimiron_url": "", "username": "liuyifu"}
EOF
  ssh liuyifu@c2-eru-1.ricebook.link -t 'sudo git --work-tree=/opt/citadel --git-dir=/opt/citadel/.git pull'
  ssh liuyifu@c2-eru-1.ricebook.link -t 'sudo systemctl restart citadel'
fi
