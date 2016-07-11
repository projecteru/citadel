# Citadel

## 什么鬼名字... 六姨夫取的, 哪天得 `ack` + `awk` 一把

## RUN

噩耗啊 gRPC 不能跟 gevent 愉快地玩耍, 只好回到原始社会, 用 `Thread` 来做异步, 用同步模式的 gunicorn, 给一个非常长时间的超时时间了.

简直是要哭瞎!!!

```
$ gunicorn --bind 0.0.0.0:5000 app:app --timeout 1200 --workers 4
```

## NOTE

一定要记得 `export GRPC_VERBOSITY=ERROR` 不然你会被 grpc 无穷无尽的 debug 输出烦死. issue 在 [这里](https://github.com/grpc/grpc/issues/6584), 找了老子好久啊... 文档好像也没有写怎么关闭的, X 了 Y 了!

## TODO

- [ ] API, deploy / build / remove / upgrade
- [ ] Publish services
- [ ] UI
