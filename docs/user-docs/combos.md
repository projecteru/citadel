## 部署套餐

部署套餐其实就是描述一下应用容器需要多少资源, 一次要部署多少个, 等等. 如果不在 `app.yaml` 里声明 `combos`, 那么在 Citadel 上操作的时候就需要手动选择 CPU, 内存, 以及其他部署参数.

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
  test:
    cpu: 0.1
    memory: "50MB"
    zone: "c1"
    podname: "develop"
    entrypoint: "web-sleep-30"
    networks:
      - "c1-test2"
    envs: "FOO=bar;"
```

另外, combos 还可以用来定义域名转发规则, 具体请阅读[域名转发](elb.md).
