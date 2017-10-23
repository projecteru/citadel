## 定时任务功能（crontab）

很多应用喜欢启动定时任务, 与其自己写一个常驻程序来执行定时任务, 不如直接用 Citadel 自带的定时任务功能: 写好配置, 然后让 Citadel 为你定时启动容器. 然而要注意:

* Citadel 只能保证**大约**准时执行, 因为 Citadel 进行调度需要时间, 容器的启动也需要时间, 经验上, 误差会在一分钟内.
* 作为 cronjob 的 entrypoint, 必须保证 Exit Code 为 0, Citadel 执行 cronjob 以后, 会自动删除返回值为 0 的容器. 如果任务执行失败导致容器无法正常退出, 将会发出报警, 并且接下来的任务将无法执行. 这个策略是为了防止平台资源被无限制占用, 所以在上线定时任务的时候, 应当努力保证命令能正常退出.
* 一个应用的 crontab, 以注册到 Citadel 上的最新版本为准, 如果 cronjob 被触发的时候, 这个版本的镜像还没有 build 完成, 那么将会直接跳过.

```
appname: "sentry"
entrypoints:
  cleanup:
    cmd: "sentry cleanup --days 7"
base: "hub.ricebook.net/base/sentry:8.7.0"
build:
  - "pip install -U -i https://pypi.doubanio.com/simple/ sentry"
combos:
  cleanup-job:
    cpu: 0.5
    memory: "512MB"
    podname: "intra"
    entrypoint: "cleanup"
    envname: "prod"
    networks:
      - "release"
crontab:
  - '0 4 * * * cleanup-job'
```
