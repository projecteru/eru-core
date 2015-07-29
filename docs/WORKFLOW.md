WORKFLOW
========

## 流程

### Pre-Deploy

1. Register
2. Build Image
3. Push Image

### Deploy

1. Pull Image
2. Deploy

### Post-Deploy

1. Broadcast containers
2. Store deploy information

## Details

* Register: 

    告诉 eru 有一个新的应用的新版本需要纳入管理, 并不会对所有的 git 版本进行管理, 只对有需要的管理.

* Build Image: 

    通过 app.yaml 里描述的 build 信息来对代码进行打包.

    1. 增加环境变量 `ENV=1`
    2. clone 代码到 /:appname 文件夹下, 并指定这里为工作目录
    3. 增加启动脚本 `/usr/local/bin/launcher`
    4. 增加名字为 :appname 的用户, 用来之后运行用户程序
    5. 按照 app.yaml 里描述的 build 信息来逐行运行构建命令 

    build 可以指定为列表, 也可以是单个值, 内容为 shell 命令接受的所有输入, 参考 [Appconfig](../Appconfig.md) 的介绍

* Push Image:

    构建好的镜像会被推送到镜像仓库

* Deploy task: 

    有两种部署策略, `centralized` 和 `average`, 一种尽可能吃完一个物理机的资源, 一种尽可能平均分布

    在目标宿主机上拉取镜像, 然后根据 app.yaml 里描述的 entrypoint 信息来启动镜像

* Broadcast:

    部署完成后会从 redis publish 出去部署完成的容器信息

------------

可以参考 [API](../API.md)
