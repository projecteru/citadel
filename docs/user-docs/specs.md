## App Specs

`app.yaml` 的作用不外乎告诉 Citadel / core 怎么部署你的应用, 包括分配资源, 在 ELB 上绑定域名转发规则, 等等. 用以下例子进行说明:

```yaml
appname: "eru"
entrypoints:
  agent:
    cmd: "/usr/bin/eru-agent"
    restart: always
    publish:
      - "12345"
    healthcheck:
      tcp_ports:
        - "12345"
    privileged: true
    log_config: "journald"
volumes:
  - "<HOST_CONFIG_DIR_PATH>:/etc/eru"
  - "/sys/fs/cgroup/:/sys/fs/cgroup/"
  - "/var/run/docker.sock:/var/run/docker.sock"
  - "/proc/:/hostProc/"
stages:
  - build
  - pack
builds:
  build:
    base: "golang:1.9.0-alpine3.6"
    # only support ssh protocol
    repo: "git@github.com:projecteru2/agent.git"
    version: "HEAD"
    dir: /go/src/github.com/projecteru2/agent
    commands:
      - apk add --no-cache git curl make
      - curl https://glide.sh/get | sh
      - make test
      - make binary
      - ./eru-agent --version
    cache:
      /go/src/github.com/projecteru2/agent/eru-agent: /usr/bin/eru-agent
      /go/src/github.com/projecteru2/agent/agent.yaml.sample: /etc/eru/agent.yaml.sample
  pack:
    base: alpine:3.6
    labels:
      ERU: 1
      version: latest
      agent: 1
    envs:
      AGENT_IN_DOCKER: 1
    commands:
      - mkdir -p /etc/eru/
```

## 卧槽好长啊快解释一下

* `appname`: 这个就是在告诉 Citadel 这个应用叫啥, 名字不允许重复, 也不允许使用下划线. 之后不管是监控数据, 还是域名, 还是日志收集, 都跟这个名字息息相关, 请用一个能让大家知道是什么意思的名字.
* `name`: 这是 core 用的, eru-core 没有 app 的概念, 于是用 name 字段对容器进行分组,  允许多个 app 共用一个 name (因为 citadel 并不关心这个字段啦), 但是不允许使用下划线.
* `entrypoints`: dict, 里面标记了多个程序的入口. 啥是入口呢? 就是你怎么样启动这个程序啊! 每个程序的入口都可以负责一些单独的功能, 同时有各种参数可以选择.
	* `cmd`: 程序启动的命令, 不同于 shell 命令, 这里无法使用 `&&` 这样的符号. 也就是说没有办法做到 `cd xxx && ./start` 这样来启动. 那如果一定要这样怎么办呢, 很简单, 你可以先写个脚本 `start`, 里面的内容就是 `cd xxx && ./start-program`, 然后在这里写 `sh start`. 另外一些环境变量也是没有办法这样使用的, 因为我们前面说了, **不同于 shell 命令**. 那么如果我要写 `./start --pid $PID_FILE` 这样的命令怎么办呢? 很简单啊, 你可以写 `sh -c './start --pid $PID_FILE'`, 用 `sh` 来启动, 可以帮你把 shell 里的一些符号先转换, 然后变成普通的命令启动. 再次重复一次, 这里**不是 shell**, 在 shell 里写的命令需要用 `sh -c 'your shell command'` 包裹起来.
	* `after_start`: 启动容器之后执行的命令, 可以当做一个 hook 使用. 比如你想看看到底进程有没有起起来啦, 就可以写一个脚本每秒钟去尝试连接, 连接成功就去啪啪啪, 然后这个脚本就可以写在这里 `after_start: "sh my_script.sh"`. 这个东西现在的用例是, apollo-mq 需要在启动之后往 start 的 API POST 一个请求过去. 然后这个 Java 进程要起起来又不知道到底要等多久, 所以写了一个脚本, 每秒尝试去 POST 那个 start 的 API, 如果成功就停止. 那么 apollo-mq 的容器起来之后就会去执行这个操作, 保证 mq 确实是 start 过的. 在这里我想严正吐槽一下 apollo-mq, 为什么一定要这样搞幺蛾子!!!
	* `before_stop`: 停止容器之前执行的命令, 也是一个 hook. 现在的用例也还是给 apollo-mq 的, 这个 mq 啊, 幺蛾子啊, 在停止容器之前得先把进程停掉, 确保不再接收任务. 所以在 stop 之前就会去 POST stop 的 API 来停掉容器, 保证先停服务, 再下容器.
	* `publish`: 需要发布到 ELB 上的端口列表, 只要写了端口, citadel 在部署的容器的时候就会对这些端口赠送 TCP 健康检查.
	* `entrypoints.image`: docker 镜像, 允许各个 entrypoint 用不同的 image 部署 (比 app 镜像拥有更高优先级).
	* `restart`: 标准的 docker restart policy.
	* `healthcheck.http_url`: 只要声明了 `ports` 就会免费送你 tcp 健康检查的, 但是写了这个健康检查 url 的话, 应用可以做更灵活准确的健康检查.tcp 健康检查的原理很简单：agent 会去尝试连接 `{容器IP}:{容器端口}` 这个地址, 连接失败认为是挂了, 修改 etcd 里容器的健康状态, 其余工作交给 citadel 来完成. http 的话 agent 会去尝试 GET `http://[IP]:[PORT]/[healthcheck.http_url]`, 你还可以声明请求 `healthcheck.http_url` 所期待的状态码, 见 `healthcheck.http_code`.
	* `healthcheck.http_port`: 用 http 来做健康检查的话, 需要声明端口.
	* `healthcheck.http_code`: 声明了健康检查 url 的期待返回值, 如果没有声明, 则认为 [200, 500) 区间的状态码都属于健康.因为这个进程还在响应请求, 这里的超时时间是 5 秒, 5 秒还没有返回认为容器不健康, 会发送报警到项目 `subscribers`.
	* `network_mode`: 如果你不想用 calico 的 SDN, 可以在这里标记为 host, 这样会占用整个宿主机的 IP, 最好不要这样, 不作死就不会死.
	* `log_config`: 可选 `json-file`, `none`, `syslog` 等, 可以覆盖整个 core 的日志配置, 也就是说可以上一个用 json-file 来记日志的容器, 方便实时 debug, 但是我们其实有其他的 debug 手段, 所以这个选项也可以无视掉, 不作死就不会死.
	* `hosts`: 可以给容器内部的 `/etc/hosts` 追加记录, 如果你有一些域名没有走 DNS 或者是需要固定 IP, 可以用这个实现, 是一个列表, 结构是 `域名:IP`, 跟 hosts 文件格式一样, 一行一个, 重复写的内容前面的会被后面的覆盖掉.
	* `dir`: core 默认的工作目录是在 `/home/{appname}`, 如果你希望切走, 可以在这里写上工作目录的绝对路径, 如果目录不存在, 那就会挂...
	* `privileged`: 容器默认使用 appname 的 user 来运行, 有时候你可能想监听 80 端口, 需要 root 权限, 这时候这里可以设置为 true, 但是请不要滥用, 万一你被人搞了进来拿到了 root 又搞了什么别的坏事... 不作死就不会死.
* `base`: 打包镜像的时候使用的基础镜像名字. 如果不写 `build`, 这里的镜像就是部署时会使用的镜像.
* `stages`: list, 描述 `builds` 下边各个 stage 的顺序.
* `builds`: dict, 包含若干个构建步骤, 也正是因为是字典, 所以需要用 `stages` 这个字段单独声明步骤的顺序.
* `volumes`: 符合 docker volume 格式的挂载方式, 格式是 `{宿主机目录}:{容器目录}` 或者 `{宿主机目录}:{容器目录}:ro`.
	```
	volumes:
	  - "/egg:/data/egg"
	```
* `dns`: 有时候你可能不想用我们默认给的 DNS, 这里可以指定外部 DNS, 一行一个, 但是, 还是那句话, 不作死就不会死.
* `subscribers`: str, 用来发送 notbot 报警消息的接收方, 例如 `#platform;sa@ricebook.com`, 具体参考 notbot 文档, notbot 将于近期开源.
* `erection_timeout`: str/int, 在进行容器换新的时候, 等待容器健康的时间. 默认为2分钟, 如果设置成0, 则会禁用平滑升级, 也就是先删除旧容器, 再启动新容器. 也可以写 [humanfriendly](https://humanfriendly.readthedocs.io/en/latest/#humanfriendly.parse_timespan) 支持的时间.
