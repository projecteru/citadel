这里介绍 Citadel 各个层面上的安全措施和权限控制.

Citadel 接入了内网 [sso](http://sso.ricebook.net/ui/) 账号, 任何鉴权功能都是用 sso 账号来实现的.

## 注册权限

想要在 Citadel 上注册一个 app, 或者更新自己的 app 的版本, 都是需要 sso auth token, 请前往 [sso auth](http://sso.ricebook.net/auth/) 页面获取. 

具体地说, 注册和 build 一个 Citadel 应用(的某一个版本), 都是需要 [`corecli`](http://gitlab.ricebook.net/platform/corecli/) 这个小工具的, 它的作用其实就是拿着你的 auth token 来调用 Citadel, 比如注册就是 `corecli register`,  build 某一个应用, 就是 `corecli build`,  `corecli` 已经内置在平台提供的各个 base 镜像里了, Citadel 应用的 gitlab repo 更新的时候, 在 ci pipeline 里会调用 `corecli` (就是在 `.gitlab-ci.yml` 里声明的).

那么, 这个 token 写到什么地方呢? 放在 `.gitlab-ci.yml` 里肯定是不安全的(虽然为了方便, 目前都是这么做的), gitlab 其实支持 Secret Variables 这种功能, 在 gitlab 项目设置 - CI/CD Pipelines 页面, 添加 `CITADEL_AUTH_TOKEN` 这个环境变量, 内容就写刚才获得的 sso auth token.

在 Citadel 刚上线的时候, 为了方便, 在教程里直接提供了 @timfeirg 或者 @tonic 的 token, 考虑安全性, 我们将会抹掉并重置教程里的 token, 项目维护者需要使用自己的 auth token.

## 项目权限以及部署权限

在 `app.yaml` 下声明 `permitted_users`, 可以控制项目权限, 比如:

```yaml
permitted_users:
  - "liuyifu"
  - "zhangye"
```

 表示 liuyifu 和 zhangye 这两个 sso 用户可以访问该应用.

在 combos 下声明 `permitted_users`, 可以限制用户的部署权限, 比如:

```yaml
combos:
  test:
    cpu: 0.3
    memory: "512MB"
    podname: "develop"
    entrypoint: "web"
    networks:
      - "c1-test"
    envs: "FOO=bar;"
    permitted_users:
      - "liuyifu"
```

这表示虽然 zhangye 和 liuyifu 都可以访问该项目, 但是 `test` 这个部署套餐只有 liuyifu 有权限部署.
如果部署套餐下边没有控制权限, 则所有具有项目权限的人都可以部署任意套餐.

**注意!** 部署套餐的权限控制, 是 UI 展示上的隐藏, 目的仅仅是防呆, 如果有项目权限的人用自己的 sso auth token 来调用 citadel 接口, 还是可以成功部署的.