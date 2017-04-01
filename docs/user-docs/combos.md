## 部署套餐

其实就是把部署参数在 `app.yaml` 创建成一个叫 `Combos` 的东西，这样在 Citadel 界面上就无需手动选择各种部署参数了：

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
      - "internal ci-test.test.ricebook.net"
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
      - "develop ci-test-c1.test.ricebook.net"
```
