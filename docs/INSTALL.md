INSTALL
=======

## 外部依赖

* Redis
* MySQL
* Docker

## 代码依赖

* pygit2
* libgit2, pygit2 的依赖, 需要额外安装, 注意版本
* Celery, 用作队列

## Install & Run

    $ git clone git@github.com:HunanTV/eru-core.git
    $ cd eru-core
    $ python setup.py install
    $ eru
