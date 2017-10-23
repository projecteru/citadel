这里介绍 Citadel 各个层面上的安全措施和权限控制.

Citadel 使用 Oauth2 进行用户登录和权限管理, 在 ENJOY 我们开发了自己的内部用户系统作为 Oauth2 server, 所有内部应用都采用 sso 登录. sso 作为一个 Oauth2 server 的示范, 将来可有可能开源出来.

## 注册权限

想要在 Citadel 上注册一个 app, 或者更新自己的 app 的版本, 都是需要 sso auth token, 请前往 sso auth 页面获取. 

具体地说, 注册和 build 一个 Citadel 应用(的某一个版本), 都是需要 eru-cli 的, 它的作用其实就是拿着你的 auth token 来调用 Citadel, 比如注册就是 `corecli register`,  build 某一个应用, 就是 `corecli build`,  `corecli` 已经内置在平台提供的各个 base 镜像里了, Citadel 应用的 gitlab repo 更新的时候, 在 ci pipeline 里会调用 `corecli` (就是在 `.gitlab-ci.yml` 里声明的).

那么, 这个 token 写到什么地方呢? 放在 `.gitlab-ci.yml` 里肯定是不安全的(虽然为了方便, 目前都是这么做的), gitlab 其实支持 Secret Variables 这种功能, 在 gitlab 项目设置 - CI/CD Pipelines 页面, 添加 `CITADEL_AUTH_TOKEN` 这个环境变量, 内容就写刚才获得的 sso auth token.

## 项目权限以及部署权限

在 `app.yaml` 下声明 `permitted_users`, 可以控制项目权限, 比如:

```yaml
permitted_users:
  - "rick"
  - "morty"
```
