## FAQ

#### 为什么把 GitLab 项目 Fork 项目到自己的仓库, 就无法在 Citadel 上 build 了?

Citadel 目前不支持 private repo build, 在平台看来, 一个线上项目, 不应该是一个私人项目. 所以如果你的项目采用 fork 来协作, 可以考虑在 `.gitlab-ci.yml` 里, 给注册到 Citadel 的任务加上 [`allow_failure: true`](https://docs.gitlab.com/ee/ci/yaml/#allow_failure). 这样即使 `corecli build` 失败, 其他的 job, 比如单元测试, 也能继续执行.

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

#### 容器里进程的运行目录是啥?

可以在 `app.yaml` 里设置 `working_dir`, 默认就是 `/home/$APPNAME`.
