这里是 Citadel 的文档, 至于 Citadel 是什么, eru-core 是什么, 在这里只能简要港下, 有兴趣了解的话, @dante 在书写 eru 项目的白皮书, 在那里会系统介绍项目架构和各个组件之间的关系.

Citadel 是容器平台的各种功能的一个集合, 它负责调用 [`eru-core`](http://gitlab.ricebook.net/platform/core) 进行容器的创建和删除, 还负责把容器的 SDN IP 更新到 [ERU Load Balancer](http://gitlab.ricebook.net/platform/erulb3/) (ELB) 上, 使之能接受来自线上的流量. 除此外, Citadel 还与我们的[内网 gitlab](http://gitlab.ricebook.net/) 进行高度集成, 你可以用 gitlab ci 给自己的应用加上 Citadel 的自动化构建, (未来)甚至滚动上线, 这部分功能是通过在 gitlab ci build 镜像里内置 [`corecli`](http://gitlab.ricebook.net/platform/corecli/) 这个小工具来实现的.

如果你只是想把自己的项目在 Citadel 上部署的话, 请阅读[上线流程](docs/user-docs/setup.md).

Changelog
==========

__2017-05-13__

  + corecli 不再对 private repo 的 build 失败做特殊处理, 参考 [FAQ](docs/user-docs/FAQ.md#fork-项目到自己的仓库以后就无法在-citadel-上-build-了?)

__2017-05-12__

  + 移除部署套餐的权限, 实现粗糙, 业务也用不到
  + hub.ricebook.net 启用 https

__2017-05-08__

  + Citadel 优化了 OPLog, 并且增加了[上线日志](http://citadel.ricebook.net/oplog/release)

__2017-04-26__

  + Citadel 迁移到 python 3, 今后只支持 python 3, 维护者请按照文档[搭建本地开发环境](docs/dev-docs/deploy.md)
  + Citadel 增加了 GitLab CI 测试流程, 并且在[开发者文档](docs/dev-docs/deploy.md)描述了开发测试流程

__2017-04-23__

  + Citadel app 的 gitlab 项目必须写项目简介, 包括用途, 是否影响线上, 可否短暂下线

__2017-04-08__

  +  强制项目维护者使用自己的 sso auth token, 详见[安全与权限](docs/user-docs/security-and-permissions.md)

__2017-04-06__

  + app.yaml 不再支持 `binds`, `mount_path`, `permdir` 这几个关键字, 统一用 `volume` 来代替, 详见[app.yaml 说明](docs/user-docs/specs.md#卧槽好长啊快解释一下)

__2017-04-01__

  + 文档开始迁移到 gitlab pages
