# 操作步骤

1. 去 sso 上获取 auth token, 然后去 gitlab 项目设置 - CI/CD Pipelines, 把 token 定义成 `CITADEL_AUTH_TOKEN` 这个变量.
2. 在项目根目录添加 `.gitlab-ci.yml`, 让 Gitlab-CI build 你的项目, build 结束以后会将该版本注册进 citadel.
3. 将项目根目录添加 `app.yaml`, 让 Citadel 知道如何部署你的项目, 以及绑定什么域名.
4. 在 citadel 上部署容器, 跑起来

## 1. 添加 `.gitlab-ci.yml`

在项目根目录添加 `.gitlab-ci.yml` 让 Gitlab CI 打包你的项目, 并且注册到 Citadel.

下边的范例基本可以照抄, **需要修改的部分已经注释**.

#### Java 项目

Java 项目在 Gitlab-CI build 阶段会打包成 `.jar` 文件生成 Gitlab artifacts, 将直接用来制作镜像, 以 [pisces-search](http://gitlab.ricebook.net/data_analysis_and_search/pisces-search/) 项目为例, 可以这样写：

```
# .gitlab-ci.yml
image: "hub.ricebook.net/base/alpine:java-2017.03.17"
variables:
  CITADEL_URL: "http://citadel.ricebook.net"
  SSO_URL: "http://sso.ricebook.net"
stages:
  - "build"
  - "core_build"

# Java 项目打包
build_job:
  stage: "build"
  script:
    # 打包命令, 请自己修改
    - "mvn --quiet clean package -Dmaven.test.skip=true"
    - "cp target/pisces-search-1.0-SNAPSHOT-exec.jar pisces-search.jar"
  # 声明 artifacts
  artifacts:
    paths:
      - "pisces-search.jar"
    expire_in: "1 week"

# 在 Core 中生成 Docker 镜像
core_build_job:
  stage: "core_build"
  allow_failure: true
  script:
    - "corecli register"
    - "corecli build --with-artifacts"

```

#### Python 项目

Python 不需要编译出二进制文件, 所以这样写就可以了：

```
# .gitlab-ci.yml
image: "hub.ricebook.net/base/centos:python-latest"
variables:
  CITADEL_URL: "http://citadel.ricebook.net"
  SSO_URL: "http://sso.ricebook.net"
stages:
  - "build"

build_job:
  stage: "build"
  allow_failure: true
  only:
    - master
  script:
    - "corecli register"
    - "corecli build"
```

base 镜像基本都是基于 Alpine 做的了, [这里](http://hub.ricebook.net/v2/base/alpine/tags/list) 是所有可用的 alpine 镜像.如果对 base 镜像有要求, 请探索 [footstone](http://gitlab.ricebook.net/footstone/), 如果没有符合要求的镜像, 请在 #sa-online 讨论.

## 2. 添加 `app.yaml`

在项目根目录添加 `app.yaml`, 让 Citadel 知道如何部署你的项目. `app.yaml` 功能丰富, 详见 [`app.yaml` 文档](user-docs/specs.md)

#### Java 项目：

```
appname: "pisces_search"
entrypoints:
  prod:
    cmd: "/opt/jdk/bin/java -Xms1g -Xmx2g  -Xmn1g -DServer=pisces-search -XX:+UseConcMarkSweepGC -XX:+CMSParallelRemarkEnabled -server -XX:SurvivorRatio=5 -XX:CMSInitiatingOccupancyFraction=80 -XX:+PrintTenuringDistribution -jar pisces-search.jar --spring.profiles.active=production"
    ports:
      - "9997/tcp"
    hosts:
      - "10-10-107-165.master:10.10.107.165"
      - "10-10-98-178.slave:10.10.98.178"
      - "10-10-111-182.slave:10.10.111.182"
  test:
    cmd: "/opt/jdk/bin/java -Xms1g -Xmx2g  -Xmn1g -DServer=pisces-search_test -XX:+UseConcMarkSweepGC -XX:+CMSParallelRemarkEnabled -server -XX:SurvivorRatio=5 -XX:CMSInitiatingOccupancyFraction=80 -XX:+PrintTenuringDistribution -jar pisces-search.jar --spring.profiles.active=test"
    ports:
      - "9997/tcp"
    hosts:
      - "10-10-107-165.master:10.10.107.165"
      - "10-10-98-178.slave:10.10.98.178"
      - "10-10-111-182.slave:10.10.111.182"
build:
  - "echo 'already done in CI'"
base: "hub.ricebook.net/base/alpine:java-2017.03.17"
permitted_users:
  - "zhangjianhua"
combos:
  prod:
    cpu: 1
    memory: "2GB"
    podname: "intra"
    entrypoint: "test"
    envname: "prod"
    networks:
      - "release"
```

#### Python 项目：

```
appname: "neptulon"
entrypoints:
  web:
    cmd: "gunicorn -c gunicorn_config.py app:app"
    ports:
      - "5000/tcp"
    restart: "always"
build:
  - "pip install -U -r requirements.txt"
base: "hub.ricebook.net/base/centos:python-latest"
permitted_users:
  - "tonic"
  - "liuyifu"
combos:
  prod:
    cpu: 0.5
    memory: "512MB"
    podname: "intra"
    entrypoint: "web"
    envname: "prod"
    networks:
      - "release"
```

## 3. 添加容器

访问 [Citadel](http://citadel.ricebook.net).

## 4. 绑定域名

见[域名绑定](elb.md)
