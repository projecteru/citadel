Citadel
=======

|coverage-status| |build-status| |docker| |docs|

Citadel 本身是联系各个 ERU 组件的一个 WEB 项目, 开发者可以用 Citadel 管理应用, 包括上下线, 在 ELB 上绑定域名, 以及一些 ERU 的运维操作. 此外, 我们在 ENJOY 用 Citadel, eru-cli, GitLab CI 搭建了一套持续集成方案.

Citadel 与 eru-core / ELB
------------------------

Citadel 负责处理应用这一概念, 包括容器的管理, ELB 流量的管理, 都可以在 Citadel 的 WEB 界面进行操作. 要知道, core 仅仅是按照一份说明书(也就是 `app.yaml`)来分配资源, 以及创建容器, 而 ELB 仅仅是根据域名转发规则进行流量转发.

Citadel 与 GitLab CI
-------------------

在 ENJOY, Citadel 和 GitLab CI 做了高度集成, 相当于在 GitLab CI 里用 eru-cli 搭建了一个 CI/CD 方案, 开发者更新了代码仓库以后, GitLab CI 会用 eru-cli 将应用的新版本注册到 Citadel 上, 并且按照 `app.yaml` 里的描述构建 Docker 镜像, 完成之后即可在 Citadel web UI 进行上线, 或者直接在 CI 流程里用 eru-cli 进行滚动上线.

Citadel API
-----------

Citadel 上所有的功能都暴露 HTTP API, 其中一个用法就是上边说到的, 使用 eru-cli + GitLab CI 作为持续集成方案, 但是开发者也可以用 Citadel API 构建特种的容器管理平台, 比如在 ENJOY, 平台组还用 Citadel API 搭建了 redis 集群. 当 Citadel 无法提供一些额外的, 特种的功能时, 仅仅使用 Citadel API, 而不使用 Citadel WEB UI 也是一个选择.

Citadel 与 eru-agent
-------------------

目前, Citadel 会读取 eru-agent 暴露出来的容器健康信息, 根据容器的健康状况来把容器发布到 ELB 上. 在[健康检查](docs/user-docs/healthcheck.md)这一节详细介绍.

.. |build-status| image:: https://travis-ci.org/projecteru2/citadel.svg?branch=master
    :alt: build status
    :scale: 100%
    :target: https://travis-ci.org/projecteru2/citadel

.. |docker| image:: https://dockerbuildbadges.quelltext.eu/status.svg?organization=niccokunzmann&repository=dockerhub-build-status-image
    :alt: docker image
    :scale: 100%
    :target: https://hub.docker.com/r/projecteru2/citadel/builds/

.. |docs| image:: https://readthedocs.org/projects/projecteru2citadel/badge/?version=latest
    :alt: Documentation Status
    :scale: 100%
    :target: https://projecteru2citadel.readthedocs.io/en/latest/?badge=latest

.. |coverage-status| image:: https://codecov.io/gh/projecteru2/citadel/branch/master/graph/badge.svg
    :alt: Coverage Status
    :scale: 100%
    :target: https://codecov.io/gh/projecteru2/citadel?branch=feature/next-gen
