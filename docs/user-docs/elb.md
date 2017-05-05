## 啥是 ELB 域名规则?

Citadel 的容器可以在 ELB 上绑定域名, ELB 就是一个支持动态修改 upstream 的 OpenResty (至少这么理解就好了).

绑定域名其实就是告诉 ELB 要把流量转发到哪个 pod 的哪些 entrypoint 的容器上, 所以一个域名绑定规则其实就是一个 `[appname]-[entrypoint]-[podname]` 元组.

## 如何绑定?

绑定域名请在 `app.yaml` 的 combo 下声明:

```
combos:
  web:
    cpu: 1
    memory: "256MB"
    podname: "intra"
    entrypoint: "web"
    envname: "prod"
    networks:
      - "release"
    elb:
    # 每个机房都有自己的 ELB，所以每个机房都要单独绑定不同的域名
      - "internal notbot.intra.ricebook.net"
  web:
    zone: "c1"
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

注意不同机房的 ELB 名字不一样, c1 的 叫 `develop`, c2 的叫做 `internal`.

定义好了以后, 在注册阶段执行 `corecli register` 的时候, 域名规则就会创建出来.

但是请注意:

* 域名可以通过 `app.yaml` 创建, 却不能通过 `app.yaml` 来删改.因为平台不知道是否会导致灾难性后果. 所以如果你修改了 entrypoint, 或者修改了 combo 里边的 podname, 需要联系平台来迁移域名 (其实就是安排时间删除老的域名绑定规则, 然后重新注册, 也就是在 gitlab 重新 build).
* 对于以下域名, sa 已经做好了通配符转发：
  * `*.ricebook.net` 和 `*.rhllor.net` 转发到 c2 ELB
  * `*.test.ricebook.net` 和 `*.test.rhllor.net` 转发到 c1 ELB

如果你要绑定的域名无法应用以上通配符转发规则, 比如 `*.ricebook.com`, 需要先在 `app.yaml` 里声明域名, 然后联系 sa 在 nginx 上进行绑定.

