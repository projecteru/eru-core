API
===

* Register app

        POST /api/app/register/

    * name: app name
    * version: app version, git revision
    * git: gitlab url, used for 'git clone ~'
    * token: gitlab token
    * appyaml: app.yaml, JSON format

* Set app env

        PUT /api/app/:appname/env

    * env: environment variables, e.g: `{"RUNENV": "PROD", "TESTING": "false"}`

* List app env content

        GET /api/app/:appname/listenv

* Deploy app on private host

        POST /api/deploy/private/:group_name/:pod_name/:app_name

    * ncore: core count for one container
    * ncontainer: how many containers to deploy
    * version: version of app
    * entrypoint: which entrypoint does container run
    * env: runtime environment

    e.g. `POST /api/deploy/private/group/pod/redis ncore=1 ncontainer=2 version=4edf51 entrypoint=rdb env=prod`

* Deploy app on public host

        POST /api/deploy/public/:group_name/:pod_name/:app_name

    * ncontainer: how many containers to deploy
    * version: version of app
    * entrypoint: which entrypoint does container run
    * env: runtime environment

    Just like above, only you can't bind your container on cores

