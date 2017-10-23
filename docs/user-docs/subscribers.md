## 订阅容器状态

请在 `app.yaml` 里声明一下 `subscribers`, 最好写 slack channel，这样容器上线、意外死亡、不健康的时候，就会发出通知.
注意，人为操作下线不会发送通知，只有容器意外退出，并且 exit code 不为 0 的时候，才会发送报警.

```
# app.yaml
subscribers: "#some-slack-channel;@your-slack-username"
```

Citadel 发送通知使用的是 `notbot`, 这意味着也可以在 `subscribers` 里写微信, 邮箱, 但是不建议这么做, 因为:

* 你希望通知到很多人, 而不是单个人, 而且极端状态下发送消息可能会比较频繁，造成不必要的打扰
* 微信发送消息有长度限制，发送有可能失败.
