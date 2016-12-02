# Citadel

## 什么鬼名字... 六姨夫取的, 哪天得 `ack` + `awk` 一把

## RUN

```shell
start web server

$ ./bin/run-web-server --reload

start etcd watcher

$ ./bin/run-etcd-watcher
```

## DEV

测试服为 http://citadel.test.ricebook.net，citadel & core 部署在 c1-eru-1。
测试自己的分支：

```shell
tools/upgrade-citadel.sh test
tools/upgrade-citadel.sh test origin feature/somefeature
tools/upgrade-citadel.sh test upstream master
```

## 升级线上

生产服部署在 c2-eru-1.

```shell
tools/upgrade-citadel.sh prod
tools/upgrade-citadel.sh prod origin feature/somefeature
tools/upgrade-citadel.sh prod upstream master
```

#### 本地搭建

```shell
python tools/flushdb.py
# inside project git@gitlab.ricebook.net:tonic/ci-test.git
corecli register
# inside project erulb: git@gitlab.ricebook.net:platform/eru-lb.git
corecli register
corecli build
```

#### Deploy

```shell
pip install -U -r requirements.txt
export GRPC_VERBOSITY=ERROR
export FLASK_APP=app.py
flask run --reload --debugger
```

## TEST

可千万别连着线上的 redis mysql 什么的就跑测试了...

```shell
$ ./bin/run-tests
```

## NOTE

一定要记得 `export GRPC_VERBOSITY=ERROR` 不然你会被 grpc 无穷无尽的 debug 输出烦死. issue 在 [这里](https://github.com/grpc/grpc/issues/6584), 找了老子好久啊... 文档好像也没有写怎么关闭的, X 了 Y 了!
