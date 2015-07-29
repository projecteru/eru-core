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

* Register: 告诉 eru 有一个新的应用的新版本需要纳入管理, 并不会对所有的 git 版本进行管理, 只对有需要的管理.
* Build Image: 通过 app.yaml 里描述的
