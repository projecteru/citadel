## 本地搭建运行环境

```shell
# setup python3 and virtualenv
brew install python3
mkvirtualenv citadel --python=python3
pip install -U -r requirements.txt
pip install -U -r requirements-dev.txt

# setup citadel database
python tools/flushdb.py

# run citadel flask app
export FLASK_APP=citadel/app.py
export GRPC_VERBOSITY=ERROR
export DEBUG=true
flask run
# 或者直接用 gunicorn 跑也可以
gunicorn citadel.app:app -c gunicorn_config.py

# 注册 ELB, cd 到 ELB 的仓库目录下
corecli register
corecli build
```

## 本地测试

可千万别连着线上的 redis mysql 什么的就跑测试了...

```shell
./bin/run-tests
```

## 线上的搭建 & 部署

#### Centos 7 下搭建 Citadel 的运行环境

```shell
# setup pyenv and python 3
curl -L https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer | bash

# add following lines to /root/.bashrc
export PATH="/root/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

source /root/.bashrc
pyenv install 3.6.1

# setup Citadel virtualenv
pyenv virtualenv 3.6.1 citadel
pyenv virtualenv activate citadel
pip install -U -r requirements.txt

# copy systemd unit files
cp tools/*.service /etc/systemd/system
systemctl daemon-reload
systemctl enable citadel citadel-worker watch-etcd
systemctl start citadel citadel-worker watch-etcd
```
