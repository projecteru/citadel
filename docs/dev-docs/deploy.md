## 开发 & 测试

#### 本地搭建运行环境

```shell
# setup python3 and virtualenv
brew install python3
mkvirtualenv citadel --python=python3
pip install -U -r requirements.txt
pip install -U -r requirements-dev.txt

# setup citadel database
python tools/flushdb.py

# inside project git@gitlab.ricebook.net:platform/ci-test.git
corecli register
# inside project erulb: git@gitlab.ricebook.net:platform/eru-lb.git
corecli register
corecli build
```

#### 本地测试

可千万别连着线上的 redis mysql 什么的就跑测试了...

```shell
$ ./bin/run-tests
```

#### 测试环境联调

有些东西可能本地还无法测试, 比如涉及到调用 eru-core 的, 所以如果你的功能涉及到调用 eru-core, 在合并分支以前还需要用脚本部署到测试环境, 人肉测试过以后再合并上线.

Citadel 自己的测试服为 http://citadel.test.ricebook.net, 和 core 一起部署在 c1-eru-2, 把 Citadel 部署到测试环境直接用脚本就可以, 不需要自己钻到服务器上去搞的, Citadel 毕竟是由3个服务组成的.

```shell
tools/deploy.sh test
tools/deploy.sh test origin feature/somefeature
tools/deploy.sh test upstream master
```

## 线上的搭建 & 部署

#### Centos 7 下搭建 Citadel 的运行环境

```shell
# setup pyenv and python 3
curl -L https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer | bash
cat >> /root/.bashrc << EOF
export PATH="/root/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
EOF
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

#### 部署 Citadel 生产环境

生产环境部署在 c2-eru-1, 和 eru-core 一起, 合并了 MR 以后, 直接在本地用脚本部署.

```shell
tools/deploy.sh prod
tools/deploy.sh prod origin feature/somefeature
tools/deploy.sh prod upstream master
```

## NOTE

一定要记得 `export GRPC_VERBOSITY=ERROR` 不然你会被 grpc 无穷无尽的 debug 输出烦死. issue 在 [这里](https://github.com/grpc/grpc/issues/6584), 找了老子好久啊... 文档好像也没有写怎么关闭的, X 了 Y 了!
