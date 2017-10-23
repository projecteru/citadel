## 定时备份容器目录

对于有状态的容器，在 `entrypoint` 下声明 `backup_path`，然后 Citadel 就会定时调用 core 接口对容器的相应目录进行备份. 至于备份的细节, 需要参考 core 的配置文档.

```
entrypoints:
  web:
    cmd: "python run.py"
    backup_path:
      - '/home/test-ci'
```
