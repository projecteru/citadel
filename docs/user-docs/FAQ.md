## FAQ

#### Fork 项目到自己的仓库以后就无法在 citadel 上 build 了？

Citadel 不支持 private repo build, 如果你的项目采用 private fork 来协作, 那么提交 merge request 的时候, 请在 git commit message 里写上 `[skip ci]`, 直接跳过 `corecli build` 步骤. Citadel 上本来就不应该部署私人项目, 而只允许部署 gitlab 组下边的项目.

但是考虑到 gitlab ci 还有跑测试的用途, 如果写 `[skip ci]` 的话, 整个 ci build 都会跳过, 还是不太好, 所以新版的 corecli 在 build private fork 的时候也能正常退出(但是其实并没有进行 build), 使得 ci build 能正常执行, 如果你的 private fork ci build 还是失败的话, 请升级一下 `gitlab-ci.yml` 里的 `image`, 具体参考[设置教程](setup.md)里边写的镜像.

#### Citadel 如何限制分支的 gitlab ci build?

在 `.gitlab-ci.yml` 里, 这样写就可以限制只在某个分支上跑 ci build.

```
only:
  - master
```

这就表示只有 `master` 分支才会触发 build. 如果其他分支也需要构建, 可以考虑去掉 `only` clause, 或者加多几个分支咯：

```
only:
  - master
  - develop
```

#### 我的应用为什么不显示 git branch？

因为 corecli 用的是旧版, 旧版在注册的时候没有提供 git branch 这个参数. 这个需要升级你的 `.gitlab-ci.yml` 里的 `image`, 为了整洁, 建议将 `app.yaml` 里的 `base` 也一并升级. 最新版的镜像请直接参考[设置教程](setup.md)的 `.gitlab-ci.yml` 和 `app.yaml`.

#### 容器里边的运行目录是啥？

默认就是应用所在的目录, 之前是 `/$APPNAME` , 为了规避安全风险, 换成了 `/home/$APPNAME`. 当然, 你可以自己在 `app.yaml` 里设置 `working_dir`.

#### 安装依赖很慢, 或者被墙了

优先选择国内源, 比如 pypi 有豆瓣和阿里云（优先考虑豆瓣）

```
pip install -U -i https://pypi.doubanio.com/simple/ sentry
pip install -U -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com sentry
```

翻墙的话, 可以参考[翻墙文档](http://phabricator.ricebook.net/w/develop/platform/gfw/)

#### 我真的很想把玩一下各种镜像

在 Mac 上[安装 Docker](https://docs.docker.com/docker-for-mac/install/), 然后在高级设置里加入 `insecure-registry` 这个参数就可以了:

```json
{
	"insecure-registries": ["hub.ricebook.net"],
}
```
