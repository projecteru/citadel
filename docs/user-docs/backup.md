## 定时备份容器目录

对于有状态的容器，在 `entrypoint` 下声明 `backup_path`，然后 citadel 就会为该容器每天6点定时备份到 `/mfs/mnt/backupdirs` 上。到了要用到备份的时候，是需要联系平台组手动处理的。

注意，在 c1 部署的容器不提供备份功能。

```
entrypoints:
  web:
    cmd: "python run.py"
    ports:
      - "5000/tcp"
    backup_path:
      - '/home/test-ci'
```
