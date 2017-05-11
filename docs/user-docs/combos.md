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
