## 定时任务功能（crontab）

在 `app.yaml` 里声明 cronjob，citadel 会为你定时启动一个容器来执行某一个 entrypoint，注意：

* 只能保证**大约**准时执行，因为citadel调度需要时间，容器的启动也需要时间
* cronjob 的 entrypoint，必须保证返回值为 0，citadel 执行 cronjob 以后，会自动删除返回值为 0 的容器。如果任务执行失败导致容器无法正常退出，接下来的任务将无法执行，并且频发报警。这个策略是为了防止平台资源被无限制占用，请理解，并且上线定时任务的时候努力保证命令能正常退出。

在 `app.yaml` 里声明 cronjob：

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
