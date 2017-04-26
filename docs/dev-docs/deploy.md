## 开发 & 测试

测试服为 http://citadel.test.ricebook.net, citadel & core 部署在 c1-eru-2, 合并分支以前请用脚本部署到测试环境, 人肉测试过以后再合并上线. 测试脚本这样用就可以:

```shell
tools/deploy.sh test
tools/deploy.sh test origin feature/somefeature
tools/deploy.sh test upstream master
```

## 升级线上

生产环境部署在 c2-eru-1.

```shell
tools/deploy.sh prod
tools/deploy.sh prod origin feature/somefeature
tools/deploy.sh prod upstream master
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

## TEST

可千万别连着线上的 redis mysql 什么的就跑测试了...

```shell
$ ./bin/run-tests
```

## NOTE

一定要记得 `export GRPC_VERBOSITY=ERROR` 不然你会被 grpc 无穷无尽的 debug 输出烦死. issue 在 [这里](https://github.com/grpc/grpc/issues/6584), 找了老子好久啊... 文档好像也没有写怎么关闭的, X 了 Y 了!
