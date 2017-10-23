## 环境变量

容器上线的时候可以指定环境变量, 各种敏感信息肯定不希望写死在代码仓库, 所以可以在 Citadel 上添加运行时的环境变量. 在 Citadel APP 界面上, 点击 • Environment Variables 就可以进行配置.

除了用户自己添加的环境变量外, 凡是 core 部署的容器里, 都注入了这样一些环境变量, 都是字面含义:

```
ERU_NODE_IP
ERU_NODE_NAME
APP_NAME
ERU_POD
ERU_ZONE
```
