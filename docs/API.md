API
===

### App

* Register app

        POST /api/app/register/

    * name: app name
    * version: app version, git revision
    * git: gitlab url, used for 'git clone ~'
    * token: gitlab token
    * appyaml: app.yaml, JSON format

* Set app environment

        PUT /api/app/:appname/env/

    * env: environment variables, e.g: `{"RUNENV": "PROD", "TESTING": "false"}`

* Get app

        GET /api/app/:name/

* Get version of app

        GET /api/app/:name/:version/

* Get environment of app

        GET /api/app/:name/:env/

* List app environment content

        GET /api/app/:appname/listenv/

* alloc app resource

        POST /api/app/alloc/:name/:env/:resource_name/:resource_alias/

        * e.g. /api/app/alooc/app1/prod/mysql/

* list containers that belongs to app

        GET /api/app/:name/containers/

* list containers in a version

        GET /api/app/:app_name/:version/containers/


### Deploy

* Deploy app on private host

        POST /api/deploy/private/:group_name/:pod_name/:app_name/

    * ncore: core count for one container
    * ncontainer: how many containers to deploy
    * version: version of app
    * entrypoint: which entrypoint does container run
    * env: runtime environment

    e.g. `POST /api/deploy/private/group/pod/redis ncore=1 ncontainer=2 version=4edf51 entrypoint=rdb env=prod`

* Deploy app on public host

        POST /api/deploy/public/:group_name/:pod_name/:app_name/

    * ncontainer: how many containers to deploy
    * version: version of app
    * entrypoint: which entrypoint does container run
    * env: runtime environment

    Just like above, only you can't bind your container on cores

* Build image

        POST /api/deploy/build/:group_name/:pod_name/:app_name/

    * base: base image
    * version: version of image

* Remove containers

        POST /api/deploy/rmcontainer/:group_name/:pod_name/:app_name/

    * version: version of app
    * host: host name
    * ncontainer: number of container you wanna remove

*  Offline a version i.e. remove a version

        POST /api/deploy/rmversion/:group_name/:pod_name/:app_name/

    * version: version name


### Container

* Get container

        GET /api/container/:container_id/
        GET /api/container/:id/

* Remove one container

        DELETE /api/container/:container_id/

* Kill container

        PUT /api/container/:container_id/kill/

* Cure container

        PUT /api/container/:container_id/cure/

* Poll container

        GET /api/container/:container_id/poll/

* Start container

        PUT /api/container/:container_id/start/

* Stop container

        PUT /api/container/:container_id/stop/

### Host

* Get host by id

        GET /api/host/:host_id/

* Get host by name

        GET /api/host/:host_name/

* Kill host

        PUT /api/host/:host_name/kill/

* Cure host

        PUT /api/host/:host_name/cure/


### Network

* Create Network

        POST /api/network/create/

    * name: ip number of network
    * netspace: id of network

* get network by id

        GET /api/network/:network_id/

* get network by name

        GET /api/network/:network_name/

* list networks

        GET /api/network/list/


### Resource

* Get host resource

        GET /api/resource/host/:host_id/resource/

* GET pod resource

        GET /api/resource/pod/:pod_id/resource/

### scale

* touch version scale infomation

        GET /api/scale/:name/:version/info/

### sys

* create group

        POST /api/sys/group/create/

    * name: the name of group you creating
    * description: descripe your group

* create pod

        POST /api/sys/pod/create/

    * name: name of pod
    * description: descripe your pod
    * core_share: how many fragments every core can divided in this pod
    * max_share_core: the max number of cores a host can share

* assign pod to a group

        POST /api/sys/pod/:pod_name/assign/
    * group_name: the name of group you wanna assign

* Create host

        POST /api/sys/host/create/

    * addr: the address of this host
    * pod_name: the name of pod this host belongs to

* Assign host to a group

        POST /api/sys/host/:address/assign/

    * group_name: the name of group you wanna assign

* get group max containers in a group

        GET /api/sys/group/:group_name/available_container_count/

    * pod_name: pod name
    * ncore: how many cores you reqire.

### task

* get a task by id

        GET /api/task/:task_id/

### Version

* Get eru version infomation

        GET /

