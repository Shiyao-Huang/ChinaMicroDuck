---
原文路径: 01_official/microduck/README.md
源仓库: https://github.com/pollen-robotics/microduck
许可证: Apache-2.0
翻译日期: 2026-09-02
---

<p align="center">
  <img src="https://github.com/user-attachments/assets/c2f7c245-8217-46a1-8d1e-e0ba967cd969" alt="microduck" width="820">
</p>

<h1 align="center">Microduck</h1>

<p align="center">
  <em>一只靠强化学习（reinforcement learning）策略驱动自己运动的小型双足机器人。</em>
</p>

<p align="center">
  <a href="https://pollen-robotics.com/microduck"><b>在这里获取你的机器鸭</b></a> ·
  <a href="docs/robot/cheatsheet.md">速查表（cheat sheet）</a> ·
  <a href="https://github.com/pollen-robotics/microduck_rl">策略训练</a> ·
  <a href="docs/design/architecture.md">工作原理</a> ·
  <a href="CONTRIBUTING.md">参与贡献</a>
</p>

<p align="center">
  <a href="https://github.com/pollen-robotics/microduck/actions/workflows/ci.yml"><img src="https://github.com/pollen-robotics/microduck/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
</p>

---

**本仓库是这只鸭子的"大脑"。** 约 25 cm、800 g 的机器人，由运行在一颗 Rockchip RK3566 上的几个守护进程（daemon）驱动：一个 50 Hz 的控制环（control loop）从神经网络策略出发驱动十五个舵机（servo），再加上无线电、摄像头，以及负责把新软件装上机器人又不把它刷成砖的整套更新机制。

运行一只 Microduck 所需的一切都在这里。**如果你想要一只，请[在这里获取](https://pollen-robotics.com/microduck)。**

它运行的策略在隔壁训练，仓库是
**[microduck_rl](https://github.com/pollen-robotics/microduck_rl)** —— MuJoCo 与 PPO、sim2real 配方，以及导出为本仓库所加载的 ONNX。

## 它会做事情

<table>
<tr>
<td width="50%">
  <video src="https://github.com/user-attachments/assets/356a6011-8e0d-4b28-bda9-da78646583a3" controls width="100%"></video>
</td>
<td width="50%">
  <video src="https://github.com/user-attachments/assets/abfbf250-1b1c-42cb-8430-00267e2b148a" controls width="100%"></video>

</td>
</tr>
<tr>
<td><b>它会走路。</b>拿起手柄就能开。</td>
<td><b>它会滑轮。</b>装上轮子，按住十字键上，它会加载另一套"大脑"。</td>
</tr>
<tr>
<td width="50%">
  <video src="https://github.com/user-attachments/assets/7e70c1da-e120-428f-ae0b-f4de62f25984" controls width="100%"></video>
</td>
<td width="50%">
  <video src="https://github.com/user-attachments/assets/3eef63a5-6f84-47cf-90de-e717e6d7f8f0" controls width="100%"></video>
</td>
</tr>
<tr>
<td><b>它会捡东西。</b>喙贴地，一个按键。</td>
<td><b>它自己会爬起来。</b>把它推倒，它会自己站好。</td>
</tr>
</table>

它还会坐下、踢球、按指令向前翻滚，并用一副只属于它自己的嗓音嘎嘎叫。

## 内容导航

### 你手里有一只鸭子

| | |
|---|---|
| [Cheat sheet](docs/robot/cheatsheet.md) | Every `robotctl` command: drive, configure, voice, chorale, theremin, wifi, updates, logs. Start here. |
| [Gamepad](docs/robot/cheatsheet.md#gamepad-configd) | The full button mapping, and pairing a pad — [once per pad](docs/robot/pair-a-gamepad.md), plus what to do when it will not bond. |
| [`duckctl`](docs/robot/duckctl.md) | The robot from a laptop over Bluetooth, with no network and no ssh. |
| [Updates](docs/robot/cheatsheet.md#updates-updaterd) | Install, roll back, pin. Every update is verified, health-gated and reversible. |

### 你想在它之上做开发

| | |
|---|---|
| [microduck_rl](https://github.com/pollen-robotics/microduck_rl) | Where the policies come from: MuJoCo, PPO, domain randomisation, and the ONNX export this repo loads. |
| [How it works](docs/design/architecture.md) | The whole system on one page — the daemons, the bus, how an update reaches a robot — then a page per part. |
| [Set up a dev board](docs/robot/install-dev.md) | From a blank board to a robot that takes branch builds. |
| [Dev cheat sheet](docs/robot/cheatsheet-dev.md) | Branch builds, release candidates, driving from a laptop, and the restart traps after an update. |
| [Push your branch](docs/robot/dev-push.md) | Build on your machine, install over ssh, about a minute. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Building, testing, layout, conventions, releasing. |
| [Docs index](docs/README.md) | Everything, including the design pages and the open problems. |

## 底层实现

Rust，不用框架，单一 workspace。`robotd` 拥有控制环与电机总线；`updaterd` 安装签名过的发布版本，并在机器人起来后不健康时回滚；`configd` 拥有 wifi 与身份；`btd` 是手机使用的蓝牙通道；`padd` 读取手柄；`mediad` 经 WebRTC 推流摄像头；`tofd` 服务深度传感器。它们通过 Unix 套接字（unix socket）上的一份 JSON-RPC 契约通信，而每个客户端 —— App、控制台、手柄、你的脚本 —— 发出的调用一模一样。

有意思的决策都写了下来：[`docs/design/`](docs/design/) 讲的是事情为什么是这个样子，[`docs/project/`](docs/project/) 讲的是出过什么问题、以及什么能了结它。

## 关于鸭子的一句话

制作这只机器人的过程中没有任何鸭子受到伤害。但咨询过几只。
