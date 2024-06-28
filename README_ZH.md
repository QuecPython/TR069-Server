# QuecPython-TR069-CWMP

中文| [English](./readme.md) 

## 概述

TR-069，全称为"Technical Report 069"，是由Broadband Forum（原DSL Forum）制定的一种应用层协议，用于远程管理和配置家庭和商业用户的宽带设备，如家庭网关、路由器和VoIP电话。该协议也称为CPE WAN Management Protocol（CWMP），它使得互联网服务提供商（ISP）能够从中心服务器上自动配置、监控和管理连接到网络的终端设备。

**Quecpython**版本的**TR069**目前主要结合了**CWMP**和**RPC**可定制的功能, 以满足客户需求, 客户只需要注册对应的时间即可处理对应的**RPC**事件来参与**ACS**与**CPE**之间的业务交互。

## 用法

- [TR069使用说明](./docs/zh/TR069使用说明.md)
- [示例代码](./code/main.py)

## 贡献

我们欢迎对本项目的改进做出贡献！请按照以下步骤进行贡献：

1. Fork 此仓库。
2. 创建一个新分支（`git checkout -b feature/your-feature`）。
3. 提交您的更改（`git commit -m 'Add your feature'`）。
4. 推送到分支（`git push origin feature/your-feature`）。
5. 打开一个 Pull Request。

## 许可证

本项目使用 Apache 许可证。详细信息请参阅 [LICENSE](./LICENSE) 文件。

## 支持

如果您有任何问题或需要支持，请参阅 [QuecPython 文档](https://python.quectel.com/doc) 或在本仓库中打开一个 issue。
