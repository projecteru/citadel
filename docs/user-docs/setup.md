# 操作步骤

1. 在项目根目录添加 `.gitlab-ci.yml`，让 Gitlab-CI build 你的项目，build 结束以后会将该版本注册进 citadel。
2. 将项目域名绑定到 ELB（eru-loadbalance），这一步在 [slack#sa-online](https://ricebook.slack.com/messages/sa-online/) 提申请，由平台负责绑定
3. 在 citadel 上部署容器，跑起来

## 1. 添加 `.gitlab-ci.yml`

在项目根目录添加 `.gitlab-ci.yml` 让 Gitlab CI 打包你的项目，并且注册到 Citadel。

下边的范例基本可以照抄，**需要修改的部分已经注释**。

#### Java 项目

Java 项目在 Gitlab-CI build 阶段会打包成 `.jar` 文件生成 Gitlab artifacts，将直接用来制作镜像，以 [pisces-search](http://gitlab.ricebook.net/data_analysis_and_search/pisces-search/) 项目为例，可以这样写：

```
# .gitlab-ci.yml
image: "hub.ricebook.net/base/alpine:java-2017.03.17"
variables:
  CITADEL_AUTH_TOKEN: "D73YeuAMzZSkoDY4FAEGRAmMKMY0Rpfv06FQEbygtEkB6TrXceeWrWcqKWAMNekL"
  CITADEL_URL: "http://citadel.ricebook.net"
  MIMIRON_URL: "http://mimiron.ricebook.net"
  SSO_URL: "http://sso.ricebook.net"
stages:
  - "build"
  - "core_build"

# Java 项目打包
build_job:
  stage: "build"
  script:
    # 打包命令，请自己修改
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
  script:
    - "corecli register"
    - "corecli --debug build --with-artifacts"

```

#### Python 项目

Python 不需要编译出二进制文件，所以这样写就可以了：

```
# .gitlab-ci.yml
image: "hub.ricebook.net/base/centos:python-latest"
variables:
  CITADEL_AUTH_TOKEN: "D73YeuAMzZSkoDY4FAEGRAmMKMY0Rpfv06FQEbygtEkB6TrXceeWrWcqKWAMNekL"
  CITADEL_URL: "http://citadel.ricebook.net"
  MIMIRON_URL: "http://mimiron.ricebook.net"
  SSO_URL: "http://sso.ricebook.net"
stages:
  - "build"

build_job:
  stage: "build"
  only:
    - master
  script:
    - "corecli --debug register"
    - "corecli --debug build"
```

base 镜像基本都是基于 Alpine 做的了，[这里](http://hub.ricebook.net/v2/base/alpine/tags/list) 是所有可用的 alpine 镜像。如果对 base 镜像有要求，请探索 [footstone](http://gitlab.ricebook.net/footstone/)，如果没有符合要求的镜像，请在 #sa-online 讨论。

## 2. 添加 `app.yaml`

在项目根目录添加 `app.yaml`，让 Citadel 知道如何部署你的项目. `app.yaml` 功能丰富, 详见 [`app.yaml` 文档](user-docs/specs.md)

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
# Citadel 项目权限
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
    # Citadel app 部署权限，只有 zhangjianhua 可以部署该 Combo
    permitted_users:
      - "zhangjianhua"
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

访问 [Citadel](http://citadel.ricebook.net)。

## 4. 绑定域名

绑定域名请在 `app.yaml` 的 combo 下声明（参考 [test-ci](http://gitlab.ricebook.net/platform/ci-test/commit/0070e269#0cf0bb82cc508190c215cbfa97023ebc538ede19_59_81) ），但是请注意：

* 域名可以通过 `app.yaml` 创建，却不能通过 `app.yaml` 来删除，或者修改。因为可能导致灾难性后果。所以如果你修改了 entrypoint，需要删除域名，然后重新注册（也就是在 gitlab 重新 build 啦）
* 对于以下域名，sa 已经做好了通配符转发：
  * `*.ricebook.net` 和 `*.rhllor.net` 转发到 c2 ELB
  * `*.test.ricebook.net` 和 `*.test.rhllor.net` 转发到 c1 ELB

如果你要绑定的域名无法应用以上通配符转发规则，比如 `*.ricebook.com`，需要先在 `app.yaml` 里声明域名，然后联系 sa 在 nginx 上进行绑定。
