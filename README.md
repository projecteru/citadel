## Citadel

[![Build Status](https://travis-ci.org/projecteru2/citadel.svg?branch=master)](https://travis-ci.org/projecteru2/citadel)

这里是 Citadel 的文档, Citadel 本身是联系各个 ERU 组件的一个 WEB 项目, 开发者可以用 Citadel 管理应用, 包括上下线, 在 ELB 上绑定域名, 以及一些 ERU 的运维操作. 此外, 我们在 ENJOY 用 Citadel, eru-cli, GitLab CI 搭建了一套持续集成方案. 目前 Citadel 还在重新开发中.

#### Citadel 与 eru-core / ELB

Citadel 负责处理应用这一概念, 包括容器的管理, ELB 流量的管理, 都可以在 Citadel 的 WEB 界面进行操作. 要知道, core 仅仅是按照一份说明书(也就是 `app.yaml`)来分配资源, 以及创建容器, 而 ELB 仅仅是根据域名转发规则进行流量转发.

#### Citadel 与 GitLab CI

在 ENJOY, Citadel 和 GitLab CI 做了高度集成, 相当于在 GitLab CI 里用 eru-cli 搭建了一个 CI/CD 方案, 开发者更新了代码仓库以后, GitLab CI 会用 eru-cli 将应用的新版本注册到 Citadel 上, 并且按照 `app.yaml` 里的描述构建 Docker 镜像, 完成之后即可在 Citadel web UI 进行上线, 或者直接在 CI 流程里用 eru-cli 进行滚动上线.

#### Citadel API

Citadel 上所有的功能都暴露 HTTP API, 其中一个用法就是上边说到的, 使用 eru-cli + GitLab CI 作为持续集成方案, 但是开发者也可以用 Citadel API 构建特种的容器管理平台, 比如在 ENJOY, 平台组还用 Citadel API 搭建了 redis 集群. 当 Citadel 无法提供一些额外的, 特种的功能时, 仅仅使用 Citadel API, 而不使用 Citadel WEB UI 也是一个选择.

#### Citadel 与 eru-agent

目前, Citadel 会读取 eru-agent 暴露出来的容器健康信息, 根据容器的健康状况来把容器发布到 ELB 上. 在[健康检查](docs/user-docs/healthcheck.md)这一节详细介绍.

Changelog
==========

__2017-07-10__

  + 还是支持 restart: always 吧

__2017-07-03__

  + 在 entrypoint 添加 image, 允许各个 entrypoint 用不同的镜像进行部署, 详见[app.yaml 说明](docs/user-docs/specs.md#卧槽好长啊快解释一下)

__2017-07-01__

  + 在 app.yaml 增加 feeze_node 选项, 详见[app.yaml 说明](docs/user-docs/specs.md#卧槽好长啊快解释一下)

__2017-06-29__

  + 在 app.yaml 增加 smooth_upgrade 选项, 允许禁用平滑升级, 详见[app.yaml 说明](docs/user-docs/specs.md#卧槽好长啊快解释一下)

__2017-06-08__

  + Citadel 移除 publisher 功能, 如果要用 etcd 记录 rpc 节点, 需要应用自己起线程去 etcd 上续命, 而不是由 Citadel 来管理

__2017-05-26__

  + 不支持 restart: always 了, 要写就写 restart: on-failure

__2017-05-18__

  + 增加迁移节点功能: 在 node 页面可以一键迁移所有容器到其他 node

__2017-05-16__

  + 用 volumes 关键字挂载目录默认给读写权限, 详见 [MR](http://gitlab.ricebook.net/platform/core/merge_requests/96)

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
