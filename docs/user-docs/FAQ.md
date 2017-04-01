## FAQ

#### Fork 项目到自己的仓库以后就无法在 citadel 上 build 了？

Citadel 不支持 private repo build，如果老项目在第一次注册到 citadel 的时候用的是个人 fork repo，那么 citadel app 里标记的仓库地址就是个人仓库了，无法收到项目组仓库的更新。如果是这种情况请在 #sa-online 提交处理。

#### Citadel 可以 build 其他分支吗？

当然可以。注意到上边的 `.gitlab-ci.yml` 示范里，每一个 build stage 都写了：

```
only:
  - master
```

这就表示只有 `master` 分支才会触发 build。如果其他分支也需要构建，可以考虑去掉 `only` clause，或者加多几个分支咯：

```
only:
  - master
  - develop
```

#### 我的 Citadel 应用无法访问 C1 机房的资源？

能 ping 通的话，试试加上连 C2 的路由：
```
route add -net 10.215.240.0/20 gw 10.10.0.1
```

#### 我的应用为什么不显示 git branch？
因为 corecli 用的是旧版，旧版在注册的时候没有提供 git branch 这个参数。这个需要升级你的 `.gitlab-ci.yml` 里的 `image`，为了整洁，建议将 `app.yaml` 里的 `base` 也一并升级。最新版的镜像请直接参考上边的 `.gitlab-ci.yml` 和 `app.yaml`。

#### 容器里边的运行目录是啥？

之前是 `/$APPNAME` ，为了规避安全风险，换成了 `/home/$APPDIR`。

#### 安装依赖很慢，或者被墙了

优先选择国内源，比如 pypi 有豆瓣和阿里云（优先考虑豆瓣）

```
pip install -U -i https://pypi.doubanio.com/simple/ sentry
pip install -U -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com sentry
```

翻墙的话，可以参考[翻墙文档](http://phabricator.ricebook.net/w/develop/platform/gfw/)
