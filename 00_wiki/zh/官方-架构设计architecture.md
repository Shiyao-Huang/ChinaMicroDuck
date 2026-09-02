---
原文路径: 01_official/microduck/docs/design/architecture.md
源仓库: https://github.com/pollen-robotics/microduck
许可证: Apache-2.0
翻译日期: 2026-09-02
---

# 机器人守护进程 —— 总体架构（Architecture）

状态：草案（draft） · 日期：2026-07-22 · 负责人：pierre

排期与里程碑见 [`roadmap.md`](../project/roadmap.md)。

本文是 [`updater-design.md`](updater-design.md) 的姊妹篇，后者详述更新系统。本文覆盖服务拆分（service split）、服务之间如何通信、状态放在哪里，以及机器人如何被控制 —— 本地、由 App、以及远程。

范围说明：本文描述的是**首个出厂版本**的目标形态，不是当前原型（`microduck_runtime`，那是探索性的、会被重写）。v1 面向**单一、明确定义的硬件配置**。

## 总体形态

一块板子上七个守护进程，通过 Unix 套接字（unix socket）通信。其中一个驱动机器人；其余之中的三个，作用是让第一个坏掉时板子不会失联；剩下的是不拥有任何东西的传输层和传感器。

```text
   gamepad          phone          you, on a laptop     a peer, anywhere    a GitHub release
      │ BLE/USB        │ BLE             │ ssh                 │ WebRTC              │ https
      ▼                ▼                 ▼                     ▼                     │
  ┌────────┐      ┌────────┐       ┌──────────┐          ┌──────────┐                │
  │  padd  │      │  btd   │       │ robotctl │          │  mediad  │                │
  └───┬────┘      └───┬────┘       └────┬─────┘          └────┬─────┘                │
      │               │  a subset of the same API             │                      │
      │  robot.*      │  robot.health · update.* · net.* · pad.* · system.*           │
      ▼               ▼                 ▼                     ▼                      │
  ┌──────────────────────────────────────────────────────────────────┐               │
  │   one unix socket per service · JSON-RPC 2.0, one object a line  │               │
  └────┬──────────────────────┬─────────────────────────┬────────────┘               │
       ▼                      ▼                         ▼                            │
  ┌───────────┐        ┌─────────────┐           ┌─────────────┐                     │
  │  robotd   │        │  configd    │           │  updaterd   │◄────────────────────┘
  │ robot.*   │        │ net.* pad.* │           │ update.*    │
  │ 50 Hz     │        │ system.*    │           │ verify      │
  │ loop      │        │ wifi, name, │           │ swap        │
  │ safety    │        │ pad bonding │           │ health gate │
  └─────┬─────┘        └──────┬──────┘           └──────┬──────┘
        │ Dynamixel           │ D-Bus                   │ systemctl restart,
        ▼                     ▼                         │ then robot.health
  15 servos + IMU      BlueZ · NetworkManager           ▼
  on one UART                                    /opt/robot/daemon/current

  ┌ publishes, answers nothing ───────────────────────────────────────┐
  │  tofd — the head's 8×8 depth matrix, on /run/tofd/tof.sock.       │
  │         mediad and robotd read it; it reads no one.               │
  └───────────────────────────────────────────────────────────────────┘
```

**`robotd` 是唯一触碰机器人的东西。** 十五个舵机和 IMU 板共享一条串行总线，50 Hz 的控制环独占它。客户端发送的是*意图*（intent）—— "走这么快"、"看那边"、"站起来" —— 由 `robotd` 内部的安全层决定什么实际可执行。系统里没有任何别的东西能指挥一台电机（[`robotd-design.md`](robotd-design.md)）。

**其中三个能在 `robotd` 死掉后继续工作。** `configd`、`updaterd` 和 `btd` 对它没有 systemd 依赖、没有 ML 运行时、也没有媒体栈，因为它们就是恢复路径：一台控制环起不来的机器人，恰恰是有人需要重新配置、更新或回滚的机器人。这也是配置放在 `configd` 而不是 `robotd` 里的原因（§1.1）。`mediad` 和 `padd` 确实依赖它，而且允许依赖：没有摄像头、没有手柄的机器人仍是一台可以更新的机器人。

**`btd`、`padd` 和 `mediad` 不拥有机器人的任何东西。** 它们是传输层。`btd` 把 API 的一个子集从 BLE 转发到能应答它的套接字；`padd` 读手柄、发送与 App 相同的意图；`mediad` 通过 WebRTC 数据通道承载相同的调用，只拥有流水线。三者都可以在不触碰机器人行为的前提下替换，而且三者每天都在被使用，所以 App 将来使用的 API 不会悄悄腐烂。`tofd` 是例外：它拥有一个传感器、发布帧、不读任何东西（§1）。

**发布版本是整体切换的，不是打补丁的。** 一次构建以完整目录的形式落在 `/opt/robot/daemon/releases/<version>/` 下；`updaterd` 校验其签名、移动 `current` 符号链接、重启各单元，然后问 `robotd` 是否健康。不健康，就自行把旧版本换回来。能越过这一关的崩溃循环会被开机计数器兜住（[`updater-design.md`](updater-design.md)）。

| service | owns | listens on | reaches out to |
|---|---|---|---|
| `robotd` | motor control, sensing, policies, safety, `robot.health` | `/run/robotd.sock` | the Dynamixel bus |
| `configd` | wifi, robot identity and name, pairing PIN, gamepad bonding, reboot | `/run/configd.sock` | BlueZ and NetworkManager over D-Bus |
| `updaterd` | releases: verify, install, swap, health-gate, roll back | `/run/updaterd.sock` | GitHub releases, `systemctl`, `robotd` |
| `btd` | nothing — BLE transport for a subset of the API | a BLE GATT service | `robotd`, `configd`, `updaterd` — not `padd` or `tofd`, whose streams a radio this narrow cannot carry |
| `padd` | nothing — gamepad transport; serves a raw input tap | `/run/padd/pad.sock` (`pad.input` only) | `/run/robotd.sock` |
| `mediad` | the camera and audio pipeline; nothing of the robot — WebRTC transport and the remote front door (§5.2) | TCP: the console on `:8080`, signalling on `:8443` — no unix socket of its own | `robotd`, `configd`, `updaterd` |
| `tofd` | the head's ToF sensor: an 8×8 depth matrix it publishes and nobody else reads | `/run/tofd/tof.sock` (`tof.stream`) | the HAT's I²C bus |
| `robotctl` | nothing — the CLI, and the tool that must work on a broken robot | — | every socket above |

状态放在哪里，以及什么能在更新后幸存：

| | |
|---|---|
| `/etc/robot/robotd.toml`, `updater.toml` | per-board configuration; the installer writes it once and never overwrites it. `robotd.toml` is read by `robotd` and — for `[media]` alone, what the camera streams — by `mediad`, so a change there restarts `mediad` rather than `robotd` |
| `/var/lib/robot/config/config.json` | robot name and pairing PIN — a file plus `flock`, owned by `configd` (§3.1) |
| NetworkManager profiles | wifi credentials; we never store them (§3) |
| `/opt/robot/daemon/releases/<ver>/` | binaries, policies and shipped defaults — replaced atomically |
| `/opt/robot/daemon/current` | the symlink that says which release is live |
| `/run/<service>/identity.json` | what each daemon is actually running, published at startup |

`releases/<ver>/` 之外的一切，在更新和回滚之后都幸存。这就是全部规则，也是为什么不把逐板配置（per-board config）打进发布版本里。

一次变更如何端到端地到达机器人：

```text
  push a branch ──► CI builds and signs a release ──► robotctl update apply
                                                            │
                                                            ▼
                                          updaterd: verify signature, unpack,
                                          move `current`, restart the units
                                                            │
                                                            ▼
                                          health gate: ask robot.health
                                            ├─ healthy  ──► keep it
                                            └─ not      ──► put the old one back
```

本文其余部分是推理过程：服务拆分（§1）、服务如何通信（§2）、谁拥有哪份状态（§3）、API 及其传输（§4）、远程访问（§5），以及安全权威放在哪里（§6）。

## 1. 服务

`systemd` 是监督者：生命周期、崩溃重启、顺序、看门狗（watchdog）。

| Service | Owns | Notes |
|---|---|---|
| `robotd` | motor control, kinematics, odometry, gait policies, sensor loop, safety | RT-ish core; authoritative on anything that can hurt the robot. Odometry is a struct in the loop, not a service: its inputs are exactly the sample the loop already read |
| `mediad` | camera/mic, encode, perception, WebRTC + remote gateway | Heaviest service; also the remote API front door (§5.2) |
| `btd` | BLE GATT server | **Transport adapter only** — owns no state (§4.1). See [`app-path-design.md`](app-path-design.md) |
| `configd` | wifi, robot identity, power, gamepad pairing | Config must be reachable when `robotd` is dead (§3.1), and `btd` must own nothing (§4.1) — so it is neither's business but its own. Gamepad pairing is here rather than in `padd` because bonding a device needs root and BlueZ, and `padd` is deliberately an unprivileged client (§4.1) |
| `tofd` | the head ToF sensor: an 8×8 depth matrix on the HAT's I²C bus | Perception, so split from `robotd` for the reason below. Owns one sensor and publishes frames; reads nothing. A board with no sensor fitted runs it anyway and says so |
| `updaterd` | update engine | See `updater-design.md` |

把 `mediad` 从 `robotd` 拆出来是有意的：媒体/感知的崩溃绝不能连累电机控制。`tofd` 是同一条规则用在更小的传感器上，具体细节本身就是理由：把一颗 VL53L5/8CX 带起来要通过 I²C 上传约 90 KB 固件、耗时数秒，总线与音频编解码器共享，而且大多数鸭子根本没装这颗传感器 —— 为它写的重试循环不属于拥有电机的那个进程。控制环里没有任何东西读深度，所以挪出去毫无损失。它也有意*不*是 `mediad` 的一部分：深度是总线上的一颗传感器，不是媒体流水线，而且在还没有摄像头可标注之前很久，它就已经有用了。

消费方以访问手柄原始流相同的方式访问它 —— 在拥有它的守护进程自己的套接字上订阅（`tof.stream`），绝不经过 `robotd`。把一帧重投影到机器人自身坐标系，意味着通过 `kinematics` crate 的头部正运动学（head FK，forward kinematics）把它与来自 `robot.state` 的关节状态结合；`tofd` 发布的是传感器的视图，不假装能算出它算不了的几何。

### 1.1 不变量

1. **`btd`、`configd` 和 `updaterd` 能在 `robotd` 死掉后继续工作。** 它们是恢复路径；它们必须在恰有什么东西坏了的情境下仍能工作。对 `robotd` 无 systemd 依赖、所有 IPC 可选且带超时、依赖面最小（无 ML 运行时、无媒体栈）。详见 `updater-design.md` §4.1。

   `configd` 出现在这份名单里是出于具体理由而非对称美观：机器人坏掉时，有人需要的恰恰是配 wifi，所以把配置放进 `robotd` 会让它在唯一要紧的场景下够不着。
2. **`robotd` 是安全的最高权威。** 任何远程或本地客户端都不能绕过跌倒检测、关节/温度限位或安全姿势逻辑。客户端发送*意图*；`robotd` 决定什么可执行。
3. **`robotd` 的控制环绝不在另一个服务上阻塞。** 所有跨服务读取都是"最新值优先"（last-value-wins）缓存，绝不同步 RPC（§2.4）。
4. **每份状态只有一个写入者。** 每个值都恰有一个拥有的服务；其他人只读或订阅。

## 2. 服务间通信

### 2.1 控制面与数据面

两种需求不同的流量。把它们混为一谈是这里的经典错误。

| | Control plane | Data plane |
|---|---|---|
| Content | commands, config, status, perception events | video/audio frames |
| Size/rate | tens of bytes, ≤100 Hz | ~27 MB/s for 640×480 RGB @30 fps |
| Mechanism | unix socket RPC | **never crosses a socket** |

### 2.2 控制面：Unix 套接字上的 JSON-RPC 2.0

- 每个服务拥有**一个 Unix 套接字**。客户端直连。N=4 的情况下没有理由上消息代理（broker）—— 总线是又一个可能出故障的组件，而且它与不变量 (1) 相抵触。
- **线上格式（wire format）：JSON-RPC 2.0，一行一个对象（NDJSON）。** 用标准协议而不是自造的：标准的请求/响应关联、标准的错误对象，还有标准的**通知（notification）** —— 它们恰好是把进度和事件流推出去的正确形态。分帧用 `tokio_util::codec::LinesCodec`；消息类型是普通的 `serde` 结构体。
- **到处都是带超时的异步，没有例外。** 任何对端都可能已死。一个关闭或沉默的套接字是正常、预期中的回答。
- 订阅是一条开放连接上的通知流。

**实测过的替代方案**（去重依赖数，ARM-Linux 目标）：

| Option | Deps | Why not |
|---|---|---|
| **JSON-RPC/NDJSON + tokio** | **30** | chosen |
| `jsonrpsee-types` only (our transport) | 36 | reasonable; declined — trades frozen-spec code for a `0.x` dependency |
| `varlink` | 24 | close in spirit; less familiar, little gained over JSON-RPC |
| `zbus` (D-Bus, p2p+blocking) | 66 | see below |
| `axum` over UDS | 66 | viable; see "HTTP/WS" below |
| `tarpc` | 71 | ergonomic Rust↔Rust, but not human-readable and server-push is awkward |
| `tonic` (gRPC) | 81 | `.proto` + codegen overhead for a handful of methods |
| `jsonrpsee-server` | 112 | **cannot serve a unix socket** — HTTP/WS transports only; `jsonrpsee-ipc` was never implemented |

依赖计数仅作记录参考，不是决定性因素。

**为什么用 Unix 套接字而不是 localhost HTTP/WS。** 功能上近乎等价；差别在访问控制和故障模式上：

- **文件系统权限就是免费的授权。** 一个 mode 0660、配专属组的套接字只有被允许的进程能访问。一个 TCP 端口对机器上所有进程和用户可达，所以得再造一层认证才能拉平。
- **`SO_PEERCRED`** 给出调用方的 uid/gid/pid，*同时*用于审计日志（"谁触发了这次回滚"是支持团队问的第一件事）和**强制执行**。两层，因为它们回答不同的问题：
  - 套接字的组（mode 0660）决定谁可以**与守护进程对话**；
  - `allow_uids`/`allow_gids` 决定谁可以**改动机器人** —— 仅限会产生改动的调用。守护进程自身运行的 uid 永远被允许（反正它有能力替换守护进程）；其他 uid 必须列在名单里，未知对端一律拒绝。
  只读调用有意不加门禁：支持团队必须能检查一台他们无权改动的机器人。在一件"面向 BLE 的服务也是客户端"的设备上，仅凭组成员资格就说"可以替换固件"太粗糙了。
- **"绑错网卡"这一类 bug 不复存在。** 因为手滑、配置错误或一个"让我的笔记本能连上"的补丁把服务绑到 `0.0.0.0`，会把*固件更新控制权*暴露给网络。在 Unix 套接字上，这种错误根本无法表达。这一条权重最高 —— 不是今天的威胁模型，而是失败模式。
- 与规划中的 **SDK** 相关：如果第三方或用户代码有朝一日在板子上运行，localhost 端口对它敞开；组所属的套接字则不然。

**为什么控制面不用 HTTP/WS**（与传输无关 —— `axum` 服务 UDS 毫无问题）：协议需要服务器到客户端的进度推送。在 HTTP 上，那意味着用 POST 承载调用、*再*用 WebSocket/SSE 承载通知 —— 两套机制，而且 `curl` 消费不了流式的那一半，可调试性的收益只覆盖请求/响应。全部走 WebSocket 恢复了一套机制，却为了得到分帧 JSON 多出一次握手，`curl` 又没了。在一条持久的 NDJSON 连接上，调用和通知是一套机制、没有握手：**概念更少，这才是真正的目标。**

**未来选项，若诊断时想要 `curl` 能力：** 在同一个 Unix 套接字上加一个小的*只读* HTTP 端点（`GET /status`、`GET /log`），提供 `curl --unix-socket … http://x/status`，而不把控制操作搬上 HTTP、也不复制流式路径。诊断与控制需求不同；拆开对两者都好。

**为什么不用 D-Bus：** BlueZ（经 `bluer`）已经把它拉进来了，所以反正都在板子上，而且 `zbus` 支持无总线的点对点。但同样的消息类型还要走 **BLE 和 WebRTC/WebSocket**（§4.1、§5.2），在那里普通的 serde 结构体行、D-Bus 类型不行。一份定义、多种传输才是目标，而 JSON 让这一切免费。我们只在操作系统要求的地方用 D-Bus（BlueZ、NetworkManager）。

**重新审视的触发条件：** 如果 `btd` 反正要为 BlueZ 深度投入 D-Bus，把更新接口也通过 `zbus` 暴露，对 `btd` 而言几乎免费，还能换来用于调试的 `busctl` 自省（introspection）。改起来便宜 —— 类型不动，只动分帧。

### 2.3 等待处异步，计算处同步

异步（tokio）用在服务真正等待的地方：长操作进行中同时服务 IPC、给对端查询或子进程设超时、取消进行中的工作。

CPU 密集和长时间的文件系统工作保持**同步**，由异步调用方交给 `spawn_blocking`。在更新器里具体是：对产物的 SHA-256、minisign 流式验签、`zstd`+`tar` 解包、以及对解包目录树的递归删除。在 Pi 上这些要跑好几秒；留在异步 worker 上，会拖住本该在更新期间持续应答 `status`/`subscribe` 的 IPC 任务。

真正快的文件系统操作 —— 符号链接的 `rename`、一次 fsync、一小段追加 —— 直接调用。把它们派给线程池得不偿失。

### 2.4 数据面：要特征，不要帧

`robotd` 不需要摄像头帧 —— 它需要*派生特征*（derived feature）（"球在 (x,y)"、"检测到人"、"响声"）。10–30 Hz、几十字节，走套接字毫无压力。

**原则：把感知放在传感器旁边。** `mediad` 拥有摄像头、跑推理、发布特征。把帧送到 `robotd` 让它自己跑视觉，会浪费板子大部分内存带宽。

**在控制环里：** `robotd` 订阅一次，读取本地缓存的*最新*快照 —— 非阻塞、最新值优先。`mediad` 卡住时只会让感知退化，而不是给电机控制添抖动。

**如果帧实在必须跨进程**（最后手段）：共享内存（shm/dmabuf 环形缓冲），套接字上只传"第 N 帧在偏移 X 处就绪"。libcamera 提供 dmabuf，所以可以做到零拷贝。优先"要特征不要帧"，避免走到这一步。

## 3. 状态归属

三类不同的状态；更新/回滚的影响见 `updater-design.md` §5.7。

| State | Owner | Mechanism |
|---|---|---|
| Wifi credentials | **NetworkManager** | We never store them. `configd` drives NM over D-Bus; NM persists profiles root-only and reconnects on its own. |
| Robot identity, user prefs, tunables | **config store** (§3.1) | File + `flock` + `rename(2)`, owned by `configd` |
| Calibration, learned state, generated per-device assets | owning service | Outside release dirs; survives update *and* rollback |
| Shipped defaults, binaries, policy bundles | update system | Under `releases/<ver>/`, swapped atomically |

让 NetworkManager 拥有 wifi 凭据：代码更少、安全性更好、要迁移的东西少一件。

**板子出厂时并没有 NetworkManager**，而上面这一行原本假设有。Armbian 的无头镜像跑的是 netplan + `systemd-networkd` + `wpa_supplicant`，而 netplan 是个配置*生成器*：它没有扫描 API，`netplan apply` 只报"配置已应用"、不报关联是否成功。这恰是一部给机器人配网的手机最需要的两件事 —— "给我看有哪些网络"和"那个密码错了" —— 所以决定维持不变，由 `scripts/migrate-network.sh` 一次性把板子迁到 NM。推理过程和在板子上的实测见 [`app-path-design.md`](app-path-design.md) §2。

### 3.1 配置存储

一个普通文件加一个小的共享 crate —— **刻意不做成服务**：

- 用 `flock` 做写串行化；写临时文件 + `rename(2)` 保证原子性。
- 用 `inotify` 做变更通知。
- 没有单点故障，任何服务挂了都仍可读，更新器也从不碰它（`updater-design.md` §5.7）。

实现位于 `configd/src/store.rs`，保存机器人名字和它的蓝牙配对 PIN。`inotify` **还**没加，是刻意的：等有*第二个*进程读这个文件时它才配存在，而今天只有 `configd` 一个。监听一个你是唯一写入者的文件，纯属仪式。

`robotd` 死掉时配置**必须**仍可达 —— 出问题时客户端需要的恰是配 wifi —— 所以它不能放在 `robotd` 里。

**配置是状态，不是动作。**"连这个 wifi"、"重启"、"应用更新"、"选模型"是动作，以 RPC 派发给拥有它的服务。

## 4. 机器人 API

### 4.1 一份定义，多种传输

`btd` **什么也不拥有**。BLE 只是几扇前门之一。如果配置或配网住在 `btd` 里，其他服务就得依赖它，SDK 也会荒谬地必须走 BLE。

```
        ┌──────── one API definition (shared crate: types + operations)
        │
   ┌────┴─────┬────────────┬──────────────┬────────────────┐
  BLE       unix socket   WebSocket     WebRTC datachannel
 (btd)      robotctl,     server-side   telepresence,
  subset    on-robot SDK  agents/LLM    full fidelity
```

每种传输都是同一 API 之上的薄适配层。BLE 暴露一个**子集**（配网、状态、更新触发/进度）—— 它太慢、限制太多，撑不起完整的 API 面，载荷也从不走它。

### 4.2 横切规则

- **按传输分别授权。** BLE 意味着物理在场 + 配对；网络传输则需要令牌（token）。同一 API、不同授权 —— 从一开始就想好检查放在哪里。
- **API 版本握手。** SDK 与守护进程的版本*一定会*漂移。一个整数，不匹配就带着清晰的提示拒绝（与 `model_api` 同一思路）。
- **意图，不是电机写。**见 §6。

## 5. 远程访问

### 5.1 需求

所有机器人与媒体数据都必须能通过 **WebRTC** 连接访问，以支持 (a) 远程临场（telepresence）和 (b) 一个观察并控制机器人的服务端程序（例如 LLM）。后者必须*容易*。

### 5.2 WebRTC 会话

一条 PeerConnection 承载一切：

```
peer (browser / phone / server)
   ├── video track(s)   ── camera
   ├── audio track(s)   ── mic + speaker (two-way for telepresence)
   ├── datachannel "control"   reliable, ordered      → the robot API (§4)
   └── datachannel "teleop"    unreliable, unordered  → input + high-rate telemetry
```

两条数据通道，呼应 §2.1：遥操作输入与遥测走**不可靠传输**（`maxRetransmits: 0`），因为重传一条 80 ms 前的摇杆指令比没用还糟 —— 永远取最新的。

**`mediad` 拥有 PeerConnection。** PC 无法跨进程拆分（轨道与数据通道共享一条 DTLS/SCTP 关联），而且它需要编码后的媒体，所以它住在 `mediad` 里，由 `mediad` 把 `control` 消息经各自的 Unix 套接字代理给拥有它的服务。因此 `mediad` 就是**远程网关**。

隔离的代价可接受：没有媒体的远程临场会话一文不值，同进程部署不会失去拆分所能保住的任何东西。本地恢复仍经 BLE / `robotctl` 独立进行（不变量 1）。

### 5.3 服务端智能体：别逼它们走 WebRTC

对 LLM 驱动的控制器而言，WebRTC 是*更难*的路。智能体不想解码一条 30 fps 的 H.264 轨 —— 它要的是每一两秒一帧，加一个状态块。先要求 ICE/DTLS/SDP 和一整套解码流水线，是笔亏本买卖。

| Consumer | Transport | Media |
|---|---|---|
| Telepresence (human) | WebRTC | tracks, low latency |
| Server-side agent / LLM | **WebSocket** | `get_frame` → JPEG on demand, or 1–2 fps push |
| On-robot SDK, `robotctl` | unix socket | snapshot API |
| App | BLE + WebRTC | as needed |

它们背后是同一个 API。"在服务器上跑一个控制机器人的 LLM"就变成：开一个 WebSocket、轮询一帧、发送意图 —— 几十行代码，没有媒体栈。这才让它真正容易。

还要注意，LLM 的延迟（几百毫秒到几秒）意味着智能体是**高层**控制器："去厨房"、"看那个人"。反应式控制留在本地的 `robotd` 里。无论用什么传输，这个切分都是正确的。

### 5.4 基础设施的清醒检查

"机器人有自己的 wifi"与"可从互联网访问"**不是**一回事。远程 WebRTC 需要：

- 一条**信令**（signaling）路径（SDP/ICE 交换），
- **STUN**，以及对称 NAT（symmetric NAT）时作为中继回退的 **TURN** —— 真实的基础设施、真实的带宽成本。

这与更新设计的"零后端"前提相矛盾。**仅限局域网的远程临场可完全避开它；互联网远程临场避不开。**悬而未决（§9）。

### 5.5 实现注记

库的选择取决于硬件编码：若要 V4L2 M2M 硬件 H.264，GStreamer `webrtcbin` 更务实；`webrtc-rs` 是纯 Rust、更容易推理，但流水线要自己搭。这会实质性地塑造 `mediad` —— 早做决定。

远程临场驾驶的延迟预算：瞄准**玻璃到玻璃（glass-to-glass）小于 200 ms**。意味着低延迟编码器设置、不用 B 帧、用 intra-refresh 而不是大关键帧。

## 6. 安全与权威

在一条会丢包的链路上远程控制一台会走路的机器人。这些设计进去比事后加装便宜得多。

- **死人开关 / 心跳。** 指令不再到达或 RTT 冲过阈值时，`robotd` 自行停住机器人。没有商量余地：网络会分区、LLM 会在推理中途卡住、笔记本会睡眠。
- **意图，不是电机写。** 远程客户端发送速度、注视目标、"坐下" —— 绝不发送原始关节指令。`robotd` 对跌倒检测、关节/温度限位和安全姿势保持最高权威。一个糊涂的智能体绝不能下出机器人会照着撞墙执行的指令。
- **显式的权威仲裁。** 实体手柄、App、远程对端和自主行为层都想掌权。要定义好的优先级与交接，而不是"谁后写谁赢"。本地/实体应能抢占远程。
- **会话上限。** v1：同时一个媒体会话，外加 M 个仅控制客户端。多方视频（simulcast、一次编码多方发送）推迟。

## 7. 隐私

这是一台放在别人家里的摄像头和麦克风。

- 启动远程会话须**明确同意**（逐次，或用户可撤销的清晰持久授权）。
- 推流进行时，机器人身上有**可见指示**。
- DTLS-SRTP 保证媒体端到端加密，**即使经过 TURN 中继** —— 值得对客户明说。
- BLE 配网写入携带 wifi 凭据：该特征（characteristic）必须配对 + 加密。

## 8. 可观测性：日志与版本

横切关注点，因为放在别人家里的机器人没法挂着调试器调试。支持团队能要到的，必须已经在机器人上。

部署细节 —— journald drop-in、安装步骤、验证命令 —— 见 [`../deploy/README.md`](../../deploy/README.md)。本节是每个服务都必须满足的契约。

### 8.1 每个服务都写日志到 stderr

`tracing` → stderr → journald，级别由 `RUST_LOG` 控制（随版本发布的单元里是 `info`）。没有服务自写日志文件：一套机制、一套保留策略、一个查看的地方。

**每个守护进程写下的第一行是它自己的身份**，级别 `warn`，所以在长期运行的板子上熬得过 `RUST_LOG=warn`：

```
WARN starting service="robotd" build=0.2.0 (rev a1b2c3d, built 2026-07-28T13:50:00Z)
     exe=/opt/robot/daemon/releases/0.2.0/bin/robotd pid=814
```

`exe` 配得上它的位置：它说明进程实际从哪个发布目录启动，这正是"更新成功了"与"符号链接动了、但 systemd 还在跑旧路径"之间的区别。

**日志量是保留策略问题，不是美观问题。**`robotd` 的逐 tick 心跳在 `debug`；在 `info` 下它每五分钟记一条摘要，带实际 tick 率占目标的百分比。逐 tick 打 `info`，一台闲置机器人一天约 8.6 万条，而在日志容量上限之下，这些条目挤走的恰是事故排查需要的日志。摘要说的还更多：一个跑在目标 60% 的控制环是活着的、并通过了健康检查，别的什么都看不出来。

### 8.2 两份记录，刻意不同的持久性

| | where | survives power loss | capped by |
|---|---|---|---|
| service logs | journald | only if configured, see `deploy/README.md` | `SystemMaxUse` |
| **update history** | `/var/lib/robot/updater/update-log.jsonl` | **yes** | 200 entries |

更新历史有意不放进日志。它住在引擎的 `state_dir`、位于 `/var/lib` 下，每条追加时都 `fsync`，重写是原子的（临时文件 + 改名 + 父目录 `fsync`）。这样"这台机器人装过什么、结果如何"在一台日志易失或被清掉的机器人上也答得上来 —— 这才是现实的支持场景，不是理想场景。

### 8.3 "正在运行的版本"与"已安装的版本"是两个不同的问题

`updaterd` 无法在更新中途重启自己（`updater-design.md` §4.1），所以每次更新后的几秒内，正在运行的二进制合法地落后于已安装的发布版本。任何只报一个版本号的工具在那个窗口内都是错的，而且错的方向会让一台正常的机器人看起来坏了。

是几秒，不是"直到重启"：引擎会安排自己的重启、以及 `btd` 在它应答后 5 秒的重启，`updaterd` 下一次启动时检查这些是否落地、把没落地的再重启（`restart-order.md` §5）。

`robotctl version` 两者都报，并点名不一致之处：

- `updaterd` 落后于已安装版本 → 短暂属正常，而且是唯一不会自愈的偏差：它由继任者报告、而不是自己重启自己，所以若持续存在，说明计划中的重启没有发生；
- `robotd` 落后 → *不*正常，因为它在 `on_apply` 的重启名单里，说明重启没有生效。

这是两种不同的诊断，绝不能共用一条消息。`--json` 为支持包提供相同内容，而且 `updaterd` **挂掉**时命令照样能用 —— 把那件事作为一行输出来报告而不是直接退出，因为那正是有人伸手拿它的时候。

版本可以从四个互不相关的地方恢复，丢一个不算事：启动日志行；走 IPC 的 `robotctl version`；每个二进制的 `--version`；以及每个发布目录里的 version.toml（外加 `robotctl update list`，它显示每个已安装版本构建自哪个修订）。

`revision` 在编译期从 `DUCK_REVISION` 注入 —— CI 会设置，本地没有，本地二进制会如实报告 `rev unknown, not a CI build`。编译期读取，绝不在运行时读 git：出厂的机器人上没有仓库。它比看上去更重要：一旦分支安装落地（roadmap M2），多个构建会共用一个版本号，修订号是区分它们的唯一东西。

### 8.4 健康是一个问题，所以它是一条命令

`robotctl health` 在一份答案里报告来自 `robotd` 的硬件与来自 `updaterd` 的软件。这不是图方便："这台机器人怎么了"在被回答*之前*分不出硬件和软件，而且一小时前回退过发布版本的机器人，与舵机没上电的机器人在两半并排上屏之前看起来一模一样。拆开会让调用方在不知道哪半有毛病之前就先选边。

机器人不健康或不可达时它**以非零值退出**，因此能给脚本把关 —— 这是建在其上的一切所依赖的契约。其余任何东西都不影响退出码：电池没电、电机过热、组件被固定（pinned），都只被报告、不被裁决。绝不能因为发布版本落在了什么状态的板子上而回滚它。

`--json` 携带相同内容，用于支持包。

## 9. 开放问题

1. **v1 的远程临场要可达互联网，还是仅限局域网？**最大的一个：无后端与运营信令 + TURN 之间的差别（§5.4）。
2. **SDK 是团队内部用还是发给最终用户？**决定 API 兼容承诺要背多硬（§4.2）。
3. App、远程对端与自主行为不一致时的**权威优先级** —— 哪怕是粗糙的固定顺序，也要是定下来的而不是涌现出来的（§6）。
4. **感知放 `mediad` 里，还是独立的 `perceptiond`？**捆绑让推理贴着摄像头、更简单；拆分则让感知崩溃杀不掉视频流。取决于视觉会做多重。
5. **行为/大脑层**（内驱、情绪、习惯）：归 `robotd`，还是独立的服务与更新通道？无论哪种，它学到的状态都是 `updater-design.md` §5.7 的素材。
6. **BLE 上的配对撤销。**没有任何东西能给手机解除配对；`bluetoothctl untrust` 是手动逃生口。需要一个 API，和一条"谁可以调用它"的规则（[`app-path-design.md`](app-path-design.md) §5）。
7. **逐设备配网状态** —— 目前只有逐机器人配对 PIN，没有别的。序列号曾是另一个竞争者，如今不再需要位置：它熔在 SoC 里、从 `/proc/device-tree/serial-number` 读取（`updater-design.md` §5.6、[`app-path-design.md`](app-path-design.md) §8.2）。PIN 不能与身份共用 —— 原计划正是共用：身份会发布在广播里，由它派生的一切都是公开的。密钥仍须在制造时生成、记录并打印。

## 10. 构建顺序

`updaterd` **先**建，然后用它来交付这套架构其余部分的每一次后续迭代。这在失败还很便宜的时候（没有客户端、没有值得弄坏的东西）把更新系统的风险前置，也意味着更新路径在机器人出厂前已被演练数百次。

在此过程中要遵守的推论：

- `updaterd` 面向 `robotd` 的**接口**（健康探测、可安全重启）构建，而不是面向实现 —— 初期用桩（stub），这也正是它可测试的原因。
- 早期的健康探测会很弱（"进程活着"）。自动回滚的置信度随 `robotd` 成熟而增长；先受考验的是*机制*本身。
- **整个早期开发期间保留一条手动恢复路径（SSH / 重刷）。**更新器既未经验证又在快速变化，而且它就装在它所更新的产物里面 —— 别让它成为唯一的退路。
- 无法事后补上的模式字段（`min_supported`、`schema_version`、`model_api`）从第一个发布版本起就在，哪怕暂时用不上。
