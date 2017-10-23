## App Specs

`app.yaml` 的作用不外乎告诉 Citadel / core 怎么部署你的应用, 包括分配资源, 在 ELB 上绑定域名转发规则, 等等. 用以下例子进行说明:

```yaml
appname: "test-ci"
entrypoints:
  test:
    after_start: "sh after_start"
    cmd: "gunicorn app:app --bind 0.0.0.0:5000"
    before_stop: "sh before_stop"
    ports:
      - "5000/tcp"
  web:
    cmd: "python run.py"
    ports:
      - "5000/tcp"
    restart: "on-failure"
    healthcheck_url: "/_test/a"
    healthcheck_expected_code: 200
  web-wrong-code:
    cmd: "python run.py"
    ports:
      - "5000/tcp"
    restart: "on-failure"
    healthcheck_url: "/_test/a"
    healthcheck_expected_code: 201
  web-bad-health:
    cmd: "python run.py --interval 15"
    ports:
      - "5000/tcp"
    healthcheck_url: "/healthcheck"
    healthcheck_expected_code: 200
build:
  - "curl www.baidu.com"
  - "pip install -r requirements.txt"
base: "hub.ricebook.net/base/alpine:python-2016.04.24"
volumes:
  - "$PERMDIR/bar:$APPDIR/bar"
dns:
  - "8.8.8.8"
  - "8.8.4.4"
meta:
  meta_key1: meta_value1
  meta_key2: meta_value2
permitted_users:
  - "cmgs"
combos:
  test-in-c2:
    cpu: 1
    memory: "512MB"
    podname: "intra"
    entrypoint: "web"
    networks:
      - "release"
    envs: "FOO=bar;"
  prod-in-c2:
    cpu: 1
    memory: "512MB"
    podname: "intra"
    entrypoint: "web"
    networks:
      - "release"
    elb:
      - "internal ci-test.test.ricebook.net"
```

## 卧槽好长啊快解释一下

* `appname`: 这个就是在告诉 Citadel 这个应用叫啥, 名字不允许重复, 也不允许使用下划线. 之后不管是监控数据, 还是域名, 还是日志收集, 都跟这个名字息息相关, 请用一个能让大家知道是什么意思的名字.
* `entrypoints`: 这是一个列表, 里面标记了多个程序的入口. 啥是入口呢? 就是你怎么样启动这个程序啊! 每个程序的入口都可以负责一些单独的功能, 同时有各种参数可以选择.
	* `cmd`: 程序启动的命令, 不同于 shell 命令, 这里无法使用 `&&` 这样的符号. 也就是说没有办法做到 `cd xxx && ./start` 这样来启动. 那如果一定要这样怎么办呢, 很简单, 你可以先写个脚本 `start`, 里面的内容就是 `cd xxx && ./start-program`, 然后在这里写 `sh start`. 另外一些环境变量也是没有办法这样使用的, 因为我们前面说了, **不同于 shell 命令**. 那么如果我要写 `./start --pid $PID_FILE` 这样的命令怎么办呢? 很简单啊, 你可以写 `sh -c './start --pid $PID_FILE'`, 用 `sh` 来启动, 可以帮你把 shell 里的一些符号先转换, 然后变成普通的命令启动. 再次重复一次, 这里**不是 shell**, 在 shell 里写的命令需要用 `sh -c 'your shell command'` 包裹起来.
	* `after_start`: 启动容器之后执行的命令, 可以当做一个 hook 使用. 比如你想看看到底进程有没有起起来啦, 就可以写一个脚本每秒钟去尝试连接, 连接成功就去啪啪啪, 然后这个脚本就可以写在这里 `after_start: "sh my_script.sh"`. 这个东西现在的用例是, apollo-mq 需要在启动之后往 start 的 API POST 一个请求过去. 然后这个 Java 进程要起起来又不知道到底要等多久, 所以写了一个脚本, 每秒尝试去 POST 那个 start 的 API, 如果成功就停止. 那么 apollo-mq 的容器起来之后就会去执行这个操作, 保证 mq 确实是 start 过的. 在这里我想严正吐槽一下 apollo-mq, 为什么一定要这样搞幺蛾子!!!
	* `before_stop`: 停止容器之前执行的命令, 也是一个 hook. 现在的用例也还是给 apollo-mq 的, 这个 mq 啊, 幺蛾子啊, 在停止容器之前得先把进程停掉, 确保不再接收任务. 所以在 stop 之前就会去 POST stop 的 API 来停掉容器, 保证先停服务, 再下容器.
	* `ports`: 是一个端口列表, 实际上只是用来告诉 citadel 和 core, 程序用了哪些端口的. 你可以选择不告诉, 但是那样自动的 ELB 绑定, health check, 都无法使用. 因为 core 不知道你跑哪里了啊! 难道你还期待 core 去帮你一个一个的 `lsof` 然后看端口查进程名字来对应么... 乖, 把你占用的端口和协议写在这里吧. 比如你在这里列出了 `5000/tcp`, 那么上一个容器时, 会自动帮你把 `{容器IP}:5000` 这个地址发布到 etcd 里去, 并且去注册到 ELB 中, 如果你有设置健康检查, 还会定时往这个地址去测试看看进程还有没有响应. 那如果你不写... 这些就都没了, 手动再见.
	* `image`: docker 镜像, 允许各个 entrypoint 用不同的 image 部署 (比 app 镜像拥有更高优先级).
	* `restart`: 标准的 docker restart policy.
	* `healthcheck_url`: 只要声明了 `ports` 就会免费送你 tcp 健康检查的, 但是写了这个健康检查 url 的话, 应用可以做更灵活准确的健康检查.tcp 健康检查的原理很简单：agent 会去尝试连接 `{容器IP}:{容器端口}` 这个地址, 连接失败认为是挂了, 修改 etcd 里容器的健康状态, 其余工作交给 citadel 来完成. http 的话 agent 会去尝试 GET `http://[IP]:[PORT]/[healthcheck_url]`, 你还可以声明请求 `healthcheck_url` 所期待的状态码, 见 `healthcheck_expected_code`.
	* `healthcheck_port`: 如果用来做健康检查的端口和暴露给 ELB 的端口不一样, 需要在这里声明.
	* `healthcheck_expected_code`: 声明了健康检查 url 的期待返回值, 如果没有声明, 则认为 [200, 500) 区间的状态码都属于健康.因为这个进程还在响应请求, 这里的超时时间是 5 秒, 5 秒还没有返回认为容器不健康, 会发送报警到项目 `subscribers`.
	* `network_mode`: 如果你不想用 calico 的 SDN, 可以在这里标记为 host, 这样会占用整个宿主机的 IP, 最好不要这样, 不作死就不会死.
	* `log_config`: 可选 `json-file`, `none`, `syslog` 等, 可以覆盖整个 core 的日志配置, 也就是说可以上一个用 json-file 来记日志的容器, 方便实时 debug, 但是我们其实有其他的 debug 手段, 所以这个选项也可以无视掉, 不作死就不会死.
	* `hosts`: 可以给容器内部的 `/etc/hosts` 追加记录, 如果你有一些域名没有走 DNS 或者是需要固定 IP, 可以用这个实现, 是一个列表, 结构是 `域名:IP`, 跟 hosts 文件格式一样, 一行一个, 重复写的内容前面的会被后面的覆盖掉.
	* `working_dir`: core 默认的工作目录是在 `/home/{appname}`, 如果你希望切走, 可以在这里写上工作目录的绝对路径, 如果目录不存在, 那就会挂...
	* `privileged`: 容器默认使用 appname 的 user 来运行, 有时候你可能想监听 80 端口, 需要 root 权限, 这时候这里可以设置为 true, 但是请不要滥用, 万一你被人搞了进来拿到了 root 又搞了什么别的坏事... 不作死就不会死.
* `base`: 打包镜像的时候使用的基础镜像名字. 如果不写 `build`, 这里的镜像就是部署时会使用的镜像.
* `build`: list, 打包镜像阶段的 shell 命令, 如果缺省, 则不为该 app 打包镜像, 部署的似乎直接用 `base` 作为镜像.
* `binds`: 不再支持, 见 `volumes`.
* `mount_path`: 不再支持, 见 `volumes`.
* `volumes`: 符合 docker volume 格式的挂载方式, 默认读写权限. 格式是 `{宿主机目录}:{容器目录}` 或者 `{宿主机目录}:{容器目录}:ro` 如果需要挂载成一个只读文件系统, 在书写 `volumes` 的时候, 右边支持展开 `$APPDIR`.
	```
	volumes:
	  - "/bar:$APPDIR/bar"
	  - "/egg:/data/egg"
	  - "/foo:$APPDIR/foo:ro"
	```
* `dns`: 有时候你可能不想用我们默认给的 DNS, 这里可以指定外部 DNS, 一行一个, 但是, 还是那句话, 不作死就不会死.
* `meta`: 用处不大, key-value 结构, 数据会被丢到容器的 labels 里去.
* `subscribers`: str, 用来发送 notbot 报警消息的接收方, 例如 `#platform;sa@ricebook.com`, 具体参考 notbot 文档, notbot 将于近期开源.
* `erection_timeout`: str/int, 如果你启用了平滑升级, 那么 Citadel 在进行容器升级或者换新的时候, 会先启动新的容器, 等待新的容器健康以后, 再删除老的容器, 默认会等待5m, 这个参数就是来控制等待时间的. 写数字的话, 单位为秒, 也可以写 [humanfriendly](https://humanfriendly.readthedocs.io/en/latest/#humanfriendly.parse_timespan) 的时间.
* `freeze_node`: bool, 如果为 true, 对容器进行升级/换新操作的时候, 会在原来的 node 上启动新容器, 否则由 eru-core 决定 node 分配. 默认为 false.
* `smooth_upgrade`: bool, 默认为 true, 也就是启用平滑升级, 有些特殊的应用不允许同一个实例有两个实例同时存活, 那么就需要禁用掉平滑升级.
* `permitted_user`: 会被加到 citade 的权限里, 这里列出的人才可以对 app 进行操作. 列出的名字是 sso.ricebook.com 里的用户名.
* `combos`: 套餐, 其实是一个自由的组合. citadel 上线的时候要选的东西太多太累了, 于是有了这么个东西. 可以直接选几号套餐然后按照套餐预先设定好的参数来部署. 是一个 key-value 结构, key 就是套餐的名字, value 就是套餐的详细参数.
	* `cpu`: float, 要多少 CPU, 注意, eru 是超售 CPU 的, 但是依然建议用多少写多少.
	* `memory`: 要多少内存, 支持单位写法, MB, GB, KB, mb, gb, kb 都可以, 但是你要是不写那个 b, 就要死了, m, g, k 都不是单位, 只是一个放大倍率而已, b 那才是单位啊, bytes 啊! 所以你要是因为没写那个 b 挂了... 不要怪我不宽容, 怪自己没文化去...
	* `podname`: 部署的区域.
	* `entrypoint`: 用上面列出的哪个 entrypoint 来部署, 如果没在里面出现那就不要怪我了...
	* `networks`: 是一个列表, 需要绑定的 calico SDN 的网络名字.
	* `elb`: 一行一个, 告诉 citadel 这个 combo 上线之后, 要去更新哪个 ELB 的哪个域名. 格式是 `[ELB Name] [域名]`.
