---
原文路径: 01_official/microduck_rl/README.md
源仓库: https://github.com/pollen-robotics/microduck_rl
许可证: Apache-2.0（代码）；3D 模型文件：CC BY-SA-NC
翻译日期: 2026-09-02
---

# Microduck RL

<img width="2215" height="884" alt="image" src="https://github.com/user-attachments/assets/5db7cc83-b3ce-4f7c-83f0-0572a63baed7" />


[Microduck](https://github.com/pollen-robotics/microduck) —— 一台约 800 g、约 25 cm 高的双足机器人 —— 的强化学习（reinforcement learning, RL）训练环境，基于
[mjlab](https://github.com/mujocolab/mjlab)（MuJoCo Warp）构建，使用 PPO。
策略在这里以 50 Hz 训练，导出为 ONNX，再由 [pollen-robotics/microduck](https://github.com/pollen-robotics/microduck) 中的运行时部署到真实机器人上。

<!-- 主打视频 —— 真机剪辑：行走、起身、侧滚、轮滑。
     保持简短（约 30 秒）且真机优先：这是"我为什么要在乎"的那一镜头。 -->

https://github.com/user-attachments/assets/50c3d537-8db2-4005-9d9c-3472faeec4d0

本仓库编码了完整的 sim2real（从仿真到现实）配方：[BAM](https://github.com/Rhoban/bam)
执行器（actuator）物理、域随机化（domain randomization）、齿隙（backlash）仿真，以及让它真正跑通的奖励设计经验
（提炼版手册见 [AGENTS.md](AGENTS.md)）。

## 快速开始

需要一块 CUDA GPU（训练经由 MuJoCo Warp 运行）和 [uv](https://docs.astral.sh/uv/)。

> **在 ARM 机器上（DGX Spark / GB10、Jetson）：**首次运行时 `uv sync` 会拉取约 2 GB 的 CUDA
> wheel，而 uv 默认 30 秒的 HTTP 超时可能在下载中途中止。
> 第一次同步前请导出 `UV_HTTP_TIMEOUT=600`。

```bash
git clone https://github.com/pollen-robotics/microduck_rl
cd microduck_rl

# train the walking policy (uses your GPU; ~1-2 h for a usable gait at 4096 envs)
uv run train Mjlab-Velocity-Flat-MicroDuck --env.scene.num-envs 4096

# watch a trained policy in the viewer
uv run play Mjlab-Velocity-Flat-MicroDuck --wandb-run-path <entity/project/run_id>

# export to ONNX for deployment
uv run scripts/export.py Mjlab-Velocity-Flat-MicroDuck --wandb-run-path <...>

# drive the exported policy in CPU MuJoCo with the keyboard
uv run scripts/infer_policy.py --walking output.onnx
```

从检查点（checkpoint）续训：

```bash
uv run train Mjlab-Velocity-Flat-MicroDuck --env.scene.num-envs 4096 \
    --agent.run-name resume --agent.load-checkpoint model_29999.pt --agent.resume True
```

没有 GPU？给任意训练命令加上 `--hf-jobs`，改为在 Hugging Face Jobs 上运行而不是本地
（见 [scripts/hf/README.md](scripts/hf/README.md)）。

## 任务

`uv run list-envs` 打印实时任务注册表。Flat/Rough（平地/崎岖）变体在注明处存在。

<!-- 展示网格 —— 每个任务族一段短 GIF（仿真或真机），每行 3 个。
     若只录几段，优先顺序：Velocity、VelStand（摔倒+恢复）、
     Roulade、SitStand、Rollers/Swizzle、BallKick。 -->

| Task id | Terrain | Description |
|---|---|---|
| `Mjlab-Velocity-{Flat,Rough}-MicroDUCK` | flat/rough | **The main task**: walking with velocity commands + head-pose commands |
| `Mjlab-VelStand-{Flat,Rough}-MicroDuck` | flat/rough | Walking + fall recovery in one policy |
| `Mjlab-StandUp-{Flat,Rough}-MicroDuck` | flat/rough | Stand up from face-down/face-up/sitting, then hold the stand + body-pose control |
| `Mjlab-SitStand-{Flat,Rough}-MicroDuck` | flat/rough | Commanded sit ↔ stand in one policy, gently, head commandable |
| `Mjlab-GroundPick-{Flat,Rough}-MicroDuck` | flat/rough | Crouch and touch the ground with the mouth tip, return to stand |
| `Mjlab-BallKick-Flat-MicroDuck` | flat | Kick a 70 mm / 15 g ball forward (actor is ball-blind) |
| `Mjlab-Roulade-Flat-MicroDuck` | flat | Forward roll over the head, land back on the feet |
| `Mjlab-Velocity-Flat-MicroDuck-Rollers` | flat | Roller-skate velocity tracking (passive wheels under the feet) |
| `Mjlab-Velocity-Swizzle-MicroDuck` | flat | Classic symmetric swizzle skating |
| `Mjlab-RollerCrouch-Flat-MicroDuck` | flat | Crouch while gliding on rollers |
| `Mjlab-RollerSlope-Flat-MicroDuck` | slope | Glide down slopes on rollers |
| `Mjlab-RollerStandUp-Flat-MicroDuck` | flat | Stand up from the ground onto the wheels |
| `Mjlab-Spin-Flat-MicroDuck` | flat | Fast spin in place on rollers |

部署时，运行时在一份共享的 61 维观测契约（observation contract）背后热切换这些策略（walk / recover / trick），所以其中任何一个都能随时接管机器人。`scripts/infer_policy.py` 排练的正是这件事：

```bash
uv run scripts/infer_policy.py --walking walk.onnx --standing stand.onnx \
    --sitstand sitstand.onnx --roulade roulade.onnx --new-cmd-obs
```

键盘驱动（速度指令、`G` 捡拾、`Y` 坐/站、`R` 侧滚、`K`/`L` 踢腿）；`--debug`、`--save-csv`、`--record` 支撑 sim2real 对比。

### 齿隙变体

每个主任务都有一个 **Backlash**（齿隙）孪生版本，在为 14 个舵机关节各串联 ±1° 齿轮空程（共 2°）的模型上训练：在任务 id 的 `MicroDuck` 前插入 `-Backlash`，例如 `Mjlab-Velocity-Flat-Backlash-MicroDuck`。

齿隙为 sim2real 做了正确建模：每个舵机得到一个无驱动的 `passive_<joint>_backlash` 铰链，而且由于真实编码器位于空程的输出侧，固件 PD 仿真（`BacklashEncoderBamActuator`）与 `joint_pos`/`joint_vel` 观测都*穿过*齿隙读取（`qpos[servo] + qpos[backlash]`）。观测与动作维度不变，因此 ONNX 导出与运行时都无需改动。
见 `src/mjlab_microduck/tasks/backlash.py`。

## 执行器模型

所有任务都使用 Dynamixel XL330 的 [BAM](https://github.com/Rhoban/bam) M6 执行器模型
（电压控制律、反电动势（back-EMF）、库仑/Stribeck/随载荷变化的摩擦），并按环境做域随机化：电池电压、负载下的电压跌落（voltage sag）、指令延迟与摩擦幅度
（`FrictionDRBamActuator`，位于 `src/mjlab_microduck/actuator/`）。

在这个尺度上 —— 微型舵机驱动一只约 800 g 的双足机器人 —— 执行器保真度占了 sim2real 差距的大头，所以执行器一路建模到电压控制律，而不是当成理想 PD。

## 机器人模型

MJCF 模型位于 `src/mjlab_microduck/robot/microduck/`，用 [onshape-to-robot](https://github.com/Rhoban/onshape-to-robot) 从 Onshape 导出，每个模型一份 `config_mjcf_*.json`：

| XML | Used by |
|---|---|
| `robot_walk.xml` | Velocity (stripped trunk/head contacts — falling is cheap) |
| `robot_allcollisions.xml` | VelStand, StandUp, SitStand, GroundPick, BallKick, Roulade (body can physically lie on the ground) |
| `robot_allcollisions_rollers.xml` | Roller tasks (passive wheels) |
| `robot_*_backlash.xml` | Backlash task variants (generated by `add_backlash.py`) |

`scene*.xml` 文件给机器人包上地面 + 关键帧（STAND/SIT/FOLD），供快速查看和 `infer_policy.py` 使用。

<!-- 配图 —— 并排渲染：walk 模型 vs rollers 模型（或碰撞几何可视化）。
     这里放一张图，模型变体的故事立刻就说清了。 -->

## 项目结构

```
src/mjlab_microduck/
├── robot/
│   ├── microduck/                    # MJCF exports, export configs, scenes, add_backlash.py
│   └── microduck_constants.py        # robot cfgs, HOME frame, BAM actuator cfg
├── actuator/friction_dr_bam.py       # BAM + friction DR + backlash encoder feedback
├── tasks/
│   ├── __init__.py                   # task registration (base + backlash variants)
│   ├── mdp.py                        # rewards, events, observations, custom classes
│   ├── backlash.py                   # make_backlash_variant() env-cfg wrapper
│   └── microduck_*_env_cfg.py        # one cfg module per task family
├── train_cli.py                      # `train` script (identical to mjlab's)
├── train_hook.py                     # intercepts `train ... --hf-jobs`
└── hf_jobs.py                        # Hugging Face Jobs submission
```

值得知道的约定：

- 观测布局（observation layout）为所有策略共享（61 维 actor 观测：48 维本体感知（proprioception）+ 指令 `[twist(3), head_pose(4), body_pose(6)]`），这正是运行时策略热切换得以可能的原因。不用某个指令槽的环境会把它零填充（zero-pad），而不是删掉。
- 无驱动关节一律命名为 `passive_*`（轮滑轮子、齿隙铰链）；执行器、关节观测与姿态奖励用 `^(?!passive_).*` 选取舵机关节。
- 域随机化开关是每个环境配置文件顶部的 `ENABLE_*` 布尔值。
- 关节布局（14 个舵机）：0–4 左腿（hip_yaw、hip_roll、hip_pitch、knee、ankle），5–8 颈/头（neck_pitch、head_pitch、head_yaw、head_roll），9–13 右腿。
- 导出器把观测归一化器（normalizer）烤进 ONNX 图 —— 永远部署 `scripts/export.py` 产出的 ONNX，绝不用手工转换的检查点，否则策略在运行时看到的是未归一化的观测。

[AGENTS.md](AGENTS.md) 记录了环境构建流程与项目一路积累的奖励设计规则（也面向在本仓库工作的 AI 编程代理）。

## 测试

```bash
uv run --with pytest pytest tests/
```

仅 CPU 的配置不变量与奖励函数回归测试 —— 它们钉死关节索引映射、奖励符号约定和 NaN 防护。

## 相关项目

- [microduck](https://github.com/pollen-robotics/microduck) —— Microduck 项目主页，包括运行导出策略的板载运行时
- [mjlab](https://github.com/mujocolab/mjlab) —— 训练框架（MuJoCo Warp + rsl_rl）
- [BAM](https://github.com/Rhoban/bam) —— 更好的执行器模型，来自 Rhoban

## 许可证

本项目采用 Apache 2.0 许可证授权。详情见 [LICENSE](LICENSE) 文件。
3D 模型文件采用知识共享 BY-SA-NC（Creative Commons BY-SA-NC）许可证授权。
