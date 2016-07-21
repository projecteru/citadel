# Citadel

## 什么鬼名字... 六姨夫取的, 哪天得 `ack` + `awk` 一把

## RUN

噩耗啊 gRPC 不能跟 gevent 愉快地玩耍, 只好回到原始社会, 用 `Thread` 来做异步, 用同步模式的 gunicorn, 给一个非常长时间的超时时间了.

简直是要哭瞎!!!

```shell
start web server

$ ./bin/run-web-server --reload

start etcd watcher

$ ./bin/run-etcd-watcher
```

## DEV

```shell
$ pip install -U -r requirements.txt
$ export GRPC_VERBOSITY=ERROR
$ export FLASK_APP=app.py
$ flask run --reload --debugger
```

跑测试.

可千万别连着线上的 redis mysql 什么的就跑测试了...

```shell
$ ./bin/run-tests
```

## NOTE

一定要记得 `export GRPC_VERBOSITY=ERROR` 不然你会被 grpc 无穷无尽的 debug 输出烦死. issue 在 [这里](https://github.com/grpc/grpc/issues/6584), 找了老子好久啊... 文档好像也没有写怎么关闭的, X 了 Y 了!

## TODO

- [x] API, deploy / build / remove / upgrade
- [x] Publish services
- [ ] UI
- [ ] 身份认证, 权限鉴定, 关系存储
- [ ] 操作日志记录
- [x] watch etcd 更改容器状态(取决于容器状态要不要直接在这里改了... 现在很简单)
