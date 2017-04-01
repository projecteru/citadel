## 容器内环境变量（ENV）

容器上线的时候可以指定环境变量，各种敏感信息不要写进repo里，尽量以环境变量的形式提供。
在 Citadel app 界面，点击 • Environment Variables 进行配置。
除了用户自己添加的环境变量外，Citadel 部署的容器里边内置以下环境变量：

```
    'ERU_NODE_IP',
    'ERU_NODE_NAME',
    'ERU_PERMDIR',
    'APP_NAME',
    'ERU_POD',
    'ERU_ZONE',
```

看名字应该能猜出含义吧，在这里不详述。
