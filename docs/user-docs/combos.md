## 部署套餐

如果不在 `app.yaml` 里声明 `combos` 的话, 每一次在 Citadel 界面上部署都要手动选择各种部署参数(cpu, memory, network 等等), 太麻烦了, 所以可以把常用的部署参数写在 `app.yaml` 里, 比如:

```
combos:
  prod:
    cpu: 1
    memory: "512MB"
    zone: "c2"
    podname: "intra"
    entrypoint: "web"
    networks:
      - "release"
    # 在 Combo 下声明 permitted_users，可以达到控制部署权限的效果
    permitted_users:
      - "liuyifu"
      - "tonic"
    # 每个机房都有自己的 ELB，所以每个机房都要单独绑定不同的域名
    elb:
      - "internal my-app.ricebook.net"
  test:
    cpu: 0.1
    memory: "50MB"
    zone: "c1"
    podname: "develop"
    entrypoint: "web-sleep-30"
    networks:
      - "c1-test2"
    envs: "FOO=bar;"
    elb:
      - "develop my-app.test.ricebook.net"
```
