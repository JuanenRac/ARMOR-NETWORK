<p align="center">
  <img src="images/ARMOR_BANNER.svg" alt="ARMOR-NETWORK banner" width="100%">
</p>

# 🛰️ ARMOR-NETWORK

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  🇨🇳 <b>简体中文</b> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### 监视本地网络：上面有哪些设备、互联网是否可用、哪些发生了变化、哪些是新的（无依赖的 Python 程序；在网络中的一台机器上运行并向 ARMOR-SERVER 报告）

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11%2B-3776ab.svg" alt="Language">
  <img src="https://img.shields.io/badge/Dependencies-none-2ea44f.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/Tests-181%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.5-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

**诚实性检查 - 今天真正能运行的部分：** 扫描器、说明发生了什么变化的清单、互联网检查、公网地址查询、来自 Studio 的指令和加密封装的登录信息，都在计算机上对照脚本化网络测试（181 个测试；每条消息都被 ARMOR-COMMON 的契约接受），程序在 CM5 测试台上作为服务运行，监视测试台所在的真实网络（一台路由器、住宅的手机和节点）。它还没有连续数周监视整个住宅，只询问路由器而从不配置它，设备是什么（类型、系统、厂商）只是猜测。它不抓包：看不到谁与谁通信，每个设备的流量和严格意义上的入侵检测需要路由器的计数器或镜像端口，那是以后的一步。

---

## 📋 速览

| | |
|---|---|
| 版本 | `0.1.5` |
| 成熟度 | 成熟 |
| 角色 | 本地网络节点：网络上有什么、发生了什么变化、互联网、来自 Studio 的指令 |
| 技术栈 | Python 3.11+，仅用标准库 |
| 测试 | 181 项（`python -m unittest discover -s tests`） |
| 契约 | 消息 `armor/network/<节点>/state`，111 个一致性向量（消息与指令） |
| 运行位置 | 被监视网络中的一台机器（Linux、Windows 或 macOS）；CM5 测试台上作为服务 |
| 真实硬件 | 在 CM5 测试台上作为服务运行，监视其真实网络（路由器、住宅的手机和节点） |
| 许可证 | GPL-3.0-or-later |

**跳转到：** [概述](#-概述) · [架构](#-架构) · [安全](#-安全与防护) · [接口](#-接口) · [配置](#-配置) · [快速开始](#-快速开始) · [测试](#-测试) · [故障排除](#-故障排除) · [结构](#-仓库结构) · [相关项目](#-相关项目)

## 🚦 项目状态

每一行是本仓库的一个部分，灯号表示它今天做到了哪一步。内容依据仓库能够展示的证据（测试、构建、运行），而不是计划。

🟢 已完成并验证 · 🟡 可用，有已知限制 · 🟠 部分完成或尚未验证 · 🔴 未完成或不可用

| 领域 | 状态 | 在这里的含义 |
|---|---|---|
| 软件 | 🟢 | 扫描器、记录变化的清单、互联网检查、公网地址查询和来自 Studio 的指令在 CM5 测试台上作为服务运行。 |
| 测试 | 🟢 | 181 项测试针对脚本化网络通过，每条消息都被 ARMOR-COMMON 的契约接受。 |
| 协议与数据 | 🟡 | 设备是什么（类型、系统、厂商）只是猜测，也不抓包：按设备统计流量和严格意义上的入侵检测尚未实现。 |
| 硬件 | 🟡 | 它监视 CM5 测试台所在的真实网络（一台路由器以及家里的手机和节点），但还没有连续数周监视整栋房子。 |
| 安全 | 🟡 | 它只查询路由器，从不配置路由器；密封的登录信息已在主机上测试，没有经过独立审查。 |
| 集成 | 🟡 | 它的消息送达 CM5 测试台的服务器和 Studio；来自 Studio 的指令已对照脚本化网络测试。 |
| 文档 | 🟢 | 八种语言和更新日志均为最新。 |

## 🎯 概述

* **网络上有什么：** 本机的邻居表、为填充它而对每个地址的试探、对每个发现的设备的回显（延迟与 TTL），以及设备对自身的宣告（mDNS、UPnP、NetBIOS、反向 DNS）。每台设备：地址、MAC、厂商（来自 IEEE 的 40,000 个块的登记表）、名称、类型、系统、开放端口及各自的应答内容，以及首次和最近一次看到的时间。
* **端口：** 对每台设备的 17（或 44）个端口进行 TCP 连接，每次十二个，最多只读取应答的几百字节；从不登录，从不利用漏洞。新设备立即检查，其余每刻钟一次。
* **变化：** 设备出现（前三次扫描只学习）、沉默或恢复、更改地址、端口打开或关闭，以及两台机器响应同一个地址（尤其是路由器的地址）。每个事件都有 id，因此只通报一次。
* **互联网：** 每隔几秒对路由器回显、一次 TCP 连接、向选定解析器发出两个 DNS 问题以及一个网页。三轮才算中断、两轮才算结束，从第一轮失败起算、数到第一轮成功，并指出是谁的问题：运营商一侧（路由器有响应而其后没有）还是本地一侧（路由器也没有响应）。延迟、丢包和最近 24 小时的中断。
* **只查看您自己的网络：** 拒绝任何非私有地址（10/8、172.16/12、192.168/16 之外）和大于 /22 的范围；排除列表让它远离脆弱的设备；不会向设备发送任何不是提问的内容。
* **消息** `armor/network/<节点>/state`：接口、互联网、每台设备和最新事件；它在共享契约中（111 个向量），只携带发现，绝不携带命令。`python -m armor_network scan` 以表格打印，`watch` 通知 ARMOR-SERVER，`demo` 演示一栋虚构的房子（新设备加入、摄像头打开 Telnet、互联网中断又恢复、有人冒充路由器应答），不触碰任何网络。
* **在哪里显示：** ARMOR-STUDIO 的网络菜单（设备、带中断和延迟的互联网、流量和事件；管理员为设备命名并标记已知设备，这会平息新设备的警报）、网络设计器（家中网络的图纸，与发现的内容对比并能自动绘制）以及 Android 应用的网络界面。警报由 ARMOR-SERVER 发出。
* **来自 Studio 的指令：**立即扫描、ping、traceroute、网络唤醒、某个设备的端口或网页，以及用你提供的登录信息进行检查；指令在对节点自身消息的应答中到达（绝不是向节点发起连接），每条在执行前都要检查，也不通过 shell 运行任何东西。
* **始终安全的登录信息：**检查所用的登录信息仅为该节点加密封装后传输，只通过 Digest 或 HTTPS 发送（绝不通过明文 HTTP 的 Basic），只发给首次见到其 HTTPS 证书的设备，并且从不回显。
* **公网一侧：**住宅的公网地址、提供者及其位置（每隔几分钟向一个固定的公共服务发一次 HTTPS 请求；`--no-public-info` 可关闭）。使用 `--dns-name` 时，还会解析从外部访问住宅所用的域名，并说明它是否指向该地址。
* **一项服务：**它作为 systemd 单元在 CM5 测试台上运行（手写，见使用指南），数据保存在自己的文件夹中。
* **尚未：** 路由器自身的计数器（按设备统计流量）、抓包、控制任何东西（封锁设备、关闭端口、修改路由器）以及在真实网络上运行数周。

## 🧩 在 A.R.M.O.R. 中的角色

ARMOR-NETWORK 是家族观察本地网络的眼睛。它运行在网络中的一台机器上（测试台上的 CM5），只看不碰，并向 [ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER) 报告，由后者保存名称、隐藏和监视的设备以及中断记录；[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO) 的*网络*菜单和*网络设计器*以及 [ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL) 的网络界面显示这些内容，Studio 还可以给它下达指令。它从不配置路由器或任何设备。

| 对话对象 | 方式 | 用途 |
|---|---|---|
| ARMOR-SERVER | 带采集令牌的 HTTP `POST`（`--server-url`） | 发送状态；指令在响应中返回 |
| MQTT | `--mqtt-url`（`mqtt://` 或 `mqtts://`） | 同一条消息也发到代理；手动指令不走这条路 |
| ARMOR-STUDIO | 经服务器 | 网络菜单和网络设计器显示它并向它下达指令 |
| ARMOR-ANDROID-CONTROL | 经服务器 | 网络界面 |
| ARMOR-COMMON | 消息与指令的契约 | `--validate` 用它检查每条消息 |

## 🏛️ 架构

<p align="center">
  <img src="images/architecture.svg" alt="ARMOR-NETWORK architecture: the local network it looks at, the modules of the node and what it tells the server, Studio and the broker" width="100%">
</p>

## 🔒 安全与防护

| 威胁 | 防御 |
|---|---|
| 扫描屋外或他人的网络 | 只扫描私有网段（10.0.0.0/8、172.16.0.0/12、192.168.0.0/16），且绝不超过 1024 个地址（/22）；`--cidr` 也必须是私有网段；防护是 `check_scan_range`，不是选项 |
| 弄坏脆弱的设备 | 跳过列表（`--skip IP`，可重复）；不向设备发送任何不是提问的内容；绝不登录、绝不利用漏洞；同时 12 个连接，只读几百字节 |
| 高风险开放端口被忽略 | 会被标记：21、23、3389、5900、6379、3306、5432、7547 和 445 |
| 注入命令的服务器指令 | 封闭列表：`scan_now`、`ping`、`traceroute`、`wake`、`ports`、`http`、`inspect`；同时最多 4 个；指令 ID 由字母、数字、`_` 和 `-` 组成（最多 32 个）；输出截断为 2000；校验 MAC；不经过 shell；指令随节点自己消息的响应到达，绝不通过连接到节点的方式 |
| 检查所用登录信息泄露 | 仅为本节点密封传输，只通过 Digest 或 HTTPS（绝不在明文 HTTP 上用 Basic），只发给首次见到其 HTTPS 证书的设备，且绝不会在响应中重复；它尝试的出厂登录来自固定列表 |
| 离开屋子的请求 | 为获取公网地址，每隔几分钟向固定的公共服务（默认 `https://ipinfo.io/json`）发一次 HTTPS 请求；`--no-public-info` 可关闭；`--dns-name` 还会检查从外部访问家的名称是否指向该地址 |

**它绝不会：** 配置路由器、抓包、封锁设备或关闭端口。设备是什么（类型、系统、厂商）只是推测。安全说明见 [docs/SAFETY.md](docs/SAFETY.md)；没有独立审查。

## 🔌 接口

| 路由 | 认证 | 作用 |
|---|---|---|
| `armor/network/<node>/state` | 消息 | 接口、互联网、每台设备和最新事件；只带发现，绝不带命令 |
| `python -m armor_network scan [--json]` | - | 查看一次网络并以表格（或消息）打印 |
| `python -m armor_network watch` | - | 持续监视；用 `--server-url` 和 `--ingest-token` 通知 ARMOR-SERVER，用 `--mqtt-url` 还通知代理 |
| `python -m armor_network demo [--count N]` | - | 虚构的房子（设备加入、摄像头开放 Telnet、互联网中断）：不会触碰任何网络 |
| `python -m armor_network internet`  `oui <mac>` | - | 一轮互联网检查；某张网卡的厂商 |

来自 Studio 的指令（`scan_now`、`ping`、`traceroute`、`wake`、`ports`、`http`、`inspect`）由 ARMOR-SERVER 的 `/api/v1/network/...` 路由排队，并在对节点消息的响应中送达；消息与指令的契约在 ARMOR-COMMON（111 个一致性向量）。见 [docs/MESSAGES.md](docs/MESSAGES.md) 和 [docs/USAGE.md](docs/USAGE.md)。

## ⚙️ 配置

| 设置 | 默认值 | 作用 |
|---|---|---|
| `--node-id` | network-1 | 此节点在消息中的名称（小写字母、数字、`-` 和 `_`） |
| `--profile {quick,standard}` | quick | 每台设备 17 或 44 个端口；新设备立即查看，其余每刻钟一次 |
| `--no-ports`  `--skip IP`  `--cidr` | - | 完全不查端口；永不探测的地址；要扫描的网络（私有，最多 1024 个地址） |
| `--scan-every`  `--internet-every` | 60 s  5 s | 扫描与互联网检查的间隔秒数 |
| `--server-url`  `--ingest-token`  `--mqtt-url`  `--mqtt-user` | - | 上报到哪里；本节点的令牌（Studio 会显示）或共享采集令牌，绝不写入文件 |
| `--data-dir` | armor-network-data | 运行之间保存清单与中断记录的位置 |
| `--validate`  `--no-public-info`  `--public-info-url`  `--dns-name` | - | 用 ARMOR-COMMON 检查每条消息；公网地址查询（关闭、其地址、要检查的名称） |

全部通过命令行选项设置（见 [docs/USAGE.md](docs/USAGE.md)，其中也给出让它常驻运行的 systemd 单元）。连续三轮失败才判定为中断，连续两轮成功才算结束；前三次扫描只用来了解有什么。

## 🚀 快速开始

**要求：** Python 3.11+（仅标准库）和被监视网络中的一台机器（Linux、Windows 或 macOS）。

```powershell
python -m unittest discover -s tests                                                 # 181 项：用真实样本的解析器、可探测范围的防护、清单、互联网、对脚本化房子运行的完整代理
python -m armor_network scan                                                         # 查看一次网络并打印（仅本机所在的私有网络）
python -m armor_network watch --server-url http://127.0.0.1:8080 --ingest-token ...  # 持续监视并通知 ARMOR-SERVER
python -m armor_network demo --count 3                                               # 虚构的房子：不碰任何网络
python tools/fetch_oui.py                                                            # 从 IEEE 注册表刷新厂商表（由人工不定期运行）
```

请参阅[用法](docs/USAGE.md)和[设计](docs/DESIGN.md)。

## 🧪 测试

```powershell
python -m unittest discover -s tests  # 181 项
python -I tools/armor_ci_validate.py
```

| 测试文件 | 测试数 | 覆盖内容 |
|---|---|---|
| `test_network.py` | 56 | 用真实样本的解析器、可探测范围的防护、清单、互联网以及对脚本化房子运行的代理 |
| `test_system_io_layer.py`  `test_system_io.py` | 39 | 真实网络层：邻居、回显、TCP、DNS |
| `test_orders.py`  `test_orders_edges.py` | 56 | 来自 Studio 的指令及其限制 |
| `test_cli_commands.py` | 20 | 命令行 |
| `test_mqtt_out.py`  `test_seal.py` | 10 | MQTT 输出与密封凭据 |

GitHub Actions 在每次推送和拉取请求时运行 A.R.M.O.R. 基线：清单、版本、更新日志和 README 一致性的校验，然后是项目自身的构建和测试。

## 🏗️ 构建与发布

这是纯 Python：无需编译。版本记录在 `pyproject.toml`、`armor.project.json` 和 README 徽章中（读取自清单）；每个版本在 [CHANGELOG.md](CHANGELOG.md) 中都有对应条目。发布版本发布在 GitHub 上。

## 🩺 故障排除

| 你看到 | 原因 | 处理 |
|---|---|---|
| `... is not a private network` 或 `... has N addresses; at most 1024` | `--cidr` 指定了公网网段或大于 /22 的网段 | 使用最多 1024 个地址的私有网段 |
| 找到的设备很少或没有 | 系统邻居表靠向每个地址探测来填充，需要 ping 或读取权限 | 以可 ping 并读取邻居表的用户权限运行 |
| 脆弱设备在扫描时异常 | 不喜欢被尝试端口 | 添加 `--skip <地址>`（可重复）或 `--no-ports` |
| Studio 一直收不到消息 | 无法连接服务器或服务器拒绝令牌（和其他问题一样被计数：`unreachable`、`unauthorized`） | 检查 `--server-url` 和令牌（Studio 显示的本节点令牌，或共享采集令牌） |

## 📂 仓库结构

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of ARMOR-NETWORK" width="100%">
</p>

<details>
<summary>目录树的文本版本</summary>

```text
ARMOR-NETWORK/
├── src/armor_network/
│   ├── ipnet.py oui.py                      可探测的范围；厂商
│   ├── system_io.py sim_io.py               真实网络；脚本网络
│   ├── neighbors.py parsers.py dnswire.py   系统和设备的回应
│   ├── services.py                          端口与推测
│   ├── inventory.py internet.py             设备与事件；中断状态机
│   ├── agent.py publisher.py mqtt_out.py    看什么；如何上报
│   ├── orders.py seal.py                    来自 Studio 的指令；密封凭据
│   ├── cli.py __main__.py                   scan、watch 和 demo
│   └── data/                                oui.tsv.gz（IEEE 注册表）
├── tests/                                   8 个模块 181 项测试
├── docs/                                    DESIGN、SAFETY、USAGE、MESSAGES
├── tools/                                   fetch_oui.py 刷新厂商注册表；共用的 CI 检查与启动器
├── images/                                  横幅图、图标和 README 的图片
├── .github/                                 CI 工作流、仪表板通知、议题和 pull request 模板
├── armor.project.json                       清单：版本、角色、成熟度
├── pyproject.toml                           包元数据、入口
├── CHANGELOG.md                             每个版本的变化
├── run.sh run.bat                           启动（共用流程）
├── build.sh build.bat                       构建并测试（共用流程）
├── build-test.sh build-test.bat             构建、测试并打包
├── test.sh test.bat                         只运行测试，不改版本
└── SECURITY.md SUPPORT.md CONTRIBUTING.md CODE_OF_CONDUCT.md LICENSE
```

</details>

## 🗺️ 路线图与已知限制

**当前已知限制**

* 还没有对整栋房子连续监视数周。
* 它只向路由器查询，从不配置路由器；设备是什么（类型、系统、厂商）只是推测。
* 它不抓包，因此看不到谁在和谁通信；按设备统计流量和严格意义上的入侵检测需要路由器的计数器或镜像端口。
* 没有独立的安全审查。

**下一步**

* 路由器自身的计数器（按设备的流量）、抓包以及在真实网络上运行数周。
* 在没有文档化风险评审的情况下，不计划控制任何东西（封锁设备、关闭端口、修改路由器）。

## 🌍 语言

README 和文本提供英语、西班牙语、法语、意大利语、德语、汉语、日语和欧洲葡萄牙语版本。

## 🔗 相关项目

**A.R.M.O.R.**（Autonomous Radar & Multimodal Observation Range）是一个由相互独立的仓库组成的周界安全系统。每个仓库都有自己的版本、自己的测试和自己的 README；这是整个系列：

* **[ARMOR-COMMON](https://github.com/JuanenRac/ARMOR-COMMON)** - 消息契约、验证器、一致性向量和生成的类型
* **[ARMOR-NODE-RADAR](https://github.com/JuanenRac/ARMOR-NODE-RADAR)** - 面向 ESP32-S3 的现场节点固件，配三个雷达和自带的网页面板
* **[ARMOR-NODE-SOLAR](https://github.com/JuanenRac/ARMOR-NODE-SOLAR)** - 太阳能逆变器和电池的协议，以及网关节点的消息
* **[ARMOR-NODE-ELECTRICAL](https://github.com/JuanenRac/ARMOR-NODE-ELECTRICAL)** - 电气节点：电表、电网读数的消息和切换规则
* **[ARMOR-NODE-ALARM](https://github.com/JuanenRac/ARMOR-NODE-ALARM)** - 报警节点与面板：防区、布防、延时、警笛和 PIN，可配合服务器也可独立使用
* **[ARMOR-NODE-HMI](https://github.com/JuanenRac/ARMOR-NODE-HMI)** - 触摸面板：壁挂屏幕上的系统状态、布防与确认，以及语音助手的所在
* **ARMOR-NETWORK**（本仓库） - 本地网络：其设备、互联网以及变化
* **[ARMOR-SERVER](https://github.com/JuanenRac/ARMOR-SERVER)** - 中央协调器：遥测、报警、设备、太阳能读数和摄像头
* **[ARMOR-STUDIO](https://github.com/JuanenRac/ARMOR-STUDIO)** - 网页控制台：摄像头、雷达、报警、太阳能以及 2D/3D 场地设计器
* **[ARMOR-ANDROID-CONTROL](https://github.com/JuanenRac/ARMOR-ANDROID-CONTROL)** - 带实时 2D/3D 雷达的 Android 操作员客户端
* **[ARMOR-IOS-CONTROL](https://github.com/JuanenRac/ARMOR-IOS-CONTROL)** - iPhone 操作员客户端
* **[ARMOR-SERVER-AI](https://github.com/JuanenRac/ARMOR-SERVER-AI)** - 视觉推理策略，会解释其决策且从不驱动设备
* **[ARMOR-VISION](https://github.com/JuanenRac/ARMOR-VISION)** - 面向 Jetson Orin NX 的摄像头区域、遮罩和检测规则
* **[ARMOR-VOICE-AI](https://github.com/JuanenRac/ARMOR-VOICE-AI)** - 离线语音意图，附带无法伪造的确认
* **[ARMOR-HARDWARE](https://github.com/JuanenRac/ARMOR-HARDWARE)** - 外壳、电子器件和台架验收矩阵
* **[ARMOR-DEVOPS](https://github.com/JuanenRac/ARMOR-DEVOPS)** - 部署、CM5 测试台、备份和 TLS
* **[ARMOR-SIMULATOR](https://github.com/JuanenRac/ARMOR-SIMULATOR)** - 带可重复故障的离线遥测模拟器
* **[ARMOR-UPDATER](https://github.com/JuanenRac/ARMOR-UPDATER)** - 检测、安装和更新生态系统自身的仓库
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - 架构、安全基线和能力矩阵

## 📚 文档

* [设计](docs/DESIGN.md)：节点如何观察、记忆和决策
* [安全](docs/SAFETY.md)：它可以触碰什么，绝不做什么
* [用法](docs/USAGE.md)：命令、选项与 systemd 单元
* [消息](docs/MESSAGES.md)：节点的消息及其指令
* [能力矩阵：哪些已被证明，哪些没有](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/CAPABILITY_MATRIX.md)
* [项目目录：版本以及各仓库之间如何相互依赖](https://github.com/JuanenRac/ARMOR-DOCS/blob/main/docs/PROJECT_CATALOG.md)
* [本仓库的更新日志](CHANGELOG.md)

## 🤝 参与贡献与社区

* 提交 pull request 之前，请运行 `python -I tools/armor_ci_validate.py` 和测试：两者都必须通过。请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 和[行为准则](CODE_OF_CONDUCT.md)。
* README 提供八种语言，由 ARMOR-DOCS 中的源文件生成：文本的修改在那里进行。
* 组件之间消息的变更从 ARMOR-COMMON 开始。
* 不要把仅仅构建过的东西描述为已在板子上运行。
* 请私下报告漏洞：[SECURITY.md](SECURITY.md)。问题、想法和报告：electrohobby3d@gmail.com（[SUPPORT.md](SUPPORT.md)）。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 许可证

GPL-3.0-or-later - 见 [LICENSE](LICENSE)。
