App Config
==========

## app.yaml 规范

### Sample:

    appname: "testapp"
    entrypoints:
        web:
            cmd: "gunicorn -b 127.0.0.1:5000 -k gevent app:app"
            ports:
                - "5000/tcp"
                - "5001/udp"
            network_mode: "bridge"
        daemon:
            cmd: "python daemon.py --interval 5"
        service:
            cmd: "python service.py --port 6000"
            ports:
                - "6000/tcp"
            network_mode: "host"
    build:
        - "apt-get update"
        - "pip install -r ./requirements.txt"
    volumes:
        - "/inside_container/data1"
        - "/inside_container/data2"
    binds:
        /on_host/data1:
            bind: "/inside_container/data1"
            ro: false
        /on_host/data2:
            bind: "/inside_container/data2"
            ro: true
            

### Explanation:
    
* `appname`, 必须, 描述这个应用的名字, 注册的时候用这个名字, 之后全部以他为主.
* `entrypoints`, 必须, 有时候存在一份代码多种用途的情况, 需要描述这个镜像的启动程序入口, 里面的entrypoint名字自定义, 在启动的时候指定.
* `cmd`, 必须, 描述这个entrypoint如何启动, 也就是启动程序的命令
* `ports`, 可选, 用于对外暴露服务端口, 如果设定了, 必须是一个列表, 格式是`端口号/协议`
* `network_mode`, 可选, 默认为`bridge`, 支持`host`.
* `build`, 必须, 描述这份代码怎么样从代码变成可以运行的环境.
* `volumes`, 可选, 挂载的本地目录, 跟`binds`配合使用.
* `binds`, 可选, 需要跟`volumes`配合使用.
