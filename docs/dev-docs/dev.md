## 开发文档

以 Mac 为例, 搭建本地开发环境步骤如下:

```
brew install mysql
mysql -uroot -e 'CREATE DATABASE citadeltest'
brew install python3
mkvirtualenv citadel --python=python3
pip install -r requirements.txt -r requirements-dev.txt
py.test --pdb -s
```

但是因为本地没有 core 可以集成测试, 如果你的开发涉及到 core, 那么请用以下步骤进行集成测试:

```
tools/deploy.sh test origin feature/next-gen
ssh c1-eru-2 -t 'sudo su'
workon citadel && cd /opt/citadel && py.test -s --pdb
```
