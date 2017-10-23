## ELB 使用文档

ELB 就是 ERU Load Balancer, 是 ERU 的核心组件之一, 这里仅仅介绍在 Citadel 上如何在 ELB 上创建出应用的域名转发规则. 如果你不熟悉 ELB 这个项目, 可以把它当做一个支持动态修改 upstream 的 Nginx.

在一个应用上线了以后, 如果希望它能通过 ELB 接受 `myapp.mycompany.com` 的流量, 需要做这样两件事:

* 在 ELB 上创建出域名转发规则, 告诉 ELB `myapp.mycompany.com` 这个域名的流量需要转发到哪个应用. 所以需要在对应的 `combos` 下面声明 `elb`, 写上域名. 然后在应用注册阶段, Citadel 会将域名转发规则写入 ELB 的 redis 配置里. 绑定域名其实就是告诉 ELB 要把流量转发到哪个 pod 的哪些 entrypoint 的容器上, 所以一个域名绑定规则其实就是一个 `[appname]-[entrypoint]-[podname]` 元组.
* 上线容器, 等容器健康以后, Citadel 会有感知, 并且把容器的 SDN IP 写到 ELB 对应的 upstream 下边, 此时 ELB 接受的流量里, `myapp.mycompany.com` 这个域名的流量就会转发到我们刚刚上线的容器里.

```
combos:
  web:
    cpu: 1
    zone: c2
    memory: "256MB"
    podname: "intra"
    entrypoint: "web"
    envname: "prod"
    networks:
      - "release"
    elb:
    # [ELB名称] [域名]
      - "internal notbot.intra.ricebook.net"
  web:
    zone: c1
    cpu: 1
    memory: "256MB"
    podname: "develop"
    entrypoint: "web"
    envname: "test"
    networks:
      - "c1-test2"
    elb:
      - "develop notbot.test.ricebook.net"
```

在 `elb` 下需要书写 ELB 的名称, 是因为生产环境中有可能有多组 ELB, 这些 ELB 各自都用 name 来进行区分.

#### 注意事项

* 域名转发规则可以通过 `app.yaml` 创建, 却不能通过 `app.yaml` 来删除, 删除应用的域名转发规则, 必须要 Citadel 管理员才能操作.
