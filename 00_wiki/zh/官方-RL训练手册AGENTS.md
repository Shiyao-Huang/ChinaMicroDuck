---
原文路径: 01_official/microduck_rl/AGENTS.md
源仓库: https://github.com/pollen-robotics/microduck_rl
许可证: Apache-2.0（代码）；3D 模型文件：CC BY-SA-NC
翻译日期: 2026-09-02
---

# AGENTS.md

Microduck —— 一台约 800 g、约 25 cm 高、装有 14 个 Dynamixel XL330 舵机的双足机器人 —— 的强化学习（RL）训练环境，基于 [mjlab](https://github.com/mujocolab/mjlab)（MuJoCo Warp）构建，使用 PPO（rsl_rl）。策略在这里以 50 Hz 训练，导出为
ONNX，再由 `pollen-robotics/microduck` 仓库中的运行时部署到真实机器人上。sim2real（从仿真到现实）迁移就是全部意义所在：下面每一条约定之所以存在，都是因为破坏它曾产出一个在查看器里能跑、上硬件就失败过的策略。

## 命令

```bash
uv run list-envs                                    # live task registry
uv run train <TASK_ID> --env.scene.num-envs 4096    # train (add --hf-jobs for Hugging Face Jobs)
uv run train <TASK_ID> --env.scene.num-envs 64 --agent.max_iterations 5   # SMOKE TEST — always run first
uv run play <TASK_ID> --wandb-run-path <entity/project/run_id>
uv run scripts/export.py <TASK_ID> --wandb-run-path <...>   # → ONNX (bakes obs normalizer — mandatory path)
uv run scripts/infer_policy.py --walking out.onnx   # CPU MuJoCo deployment rehearsal
uv run --with pytest pytest tests/
```

在 64 个环境上跑 5 次迭代的冒烟测试（smoke test），花几美分就能抓住约 95% 的配置错误。
绝不在没有冒烟测试的情况下发起长时间训练。

## 仓库地图

- `src/mjlab_microduck/tasks/mdp.py` —— 全部自定义 MDP 函数（奖励、事件、观测、指令、课程）。新函数加在这里，按任务分组。
- `src/mjlab_microduck/tasks/microduck_*_env_cfg.py` —— 每个任务族一个配置模块。`microduck_velocity_env_cfg.py` 是主行走配方，也是其他环境构建或镜像的共享基座（机器人、域随机化、观测、指令）。
- `src/mjlab_microduck/tasks/__init__.py` —— 任务注册（基础版 + `-Backlash-` 变体）。
- `src/mjlab_microduck/tasks/backlash.py` —— 把任意环境配置包装成它的齿隙孪生版。
- `src/mjlab_microduck/robot/microduck_constants.py` —— 机器人配置、HOME 坐标系、BAM 执行器配置。
- `src/mjlab_microduck/robot/microduck/` —— 从 Onshape 导出的 MJCF
  （onshape-to-robot，每个模型一份 `config_mjcf_*.json`）+ 场景 + `add_backlash.py`。
- `src/mjlab_microduck/actuator/friction_dr_bam.py` —— BAM 执行器 + 摩擦域随机化 + 齿隙编码器。
- `scripts/` —— 导出、推理、sim2real 对比、wandb 辅助脚本。
- `tests/` —— 配置不变量与 MDP 函数回归测试（CPU，无需 GPU）。

## 不变量 —— 不要破坏这些

- **观测布局是 61 维（actor）且为整个策略家族共享**，因此策略可在运行时热切换：48 维基础本体感知 +
  13 维指令块 `[twist(3), head_pose(4), body_pose(6)]`，顺序固定。不用某个指令槽的环境必须把它零填充（保留观测项、采样极小范围） —— 绝不删除槽位。
- **关节布局**（14 个舵机，在 walk/allcollisions 模型上 ctrl 索引 = 关节索引）：0–4 左腿（hip_yaw、hip_roll、hip_pitch、knee、ankle），5–8
  颈/头（neck_pitch、head_pitch、head_yaw、head_roll），9–13 右腿。
  在 roller/backlash 模型上，被动关节是交错插入的 —— 绝不在 MDP 函数里硬编码关节索引；使用 mdp.py 里的 `_servo_joint_ids` / `_servo_joint_pos` 辅助函数（在普通模型上是恒等映射，在其他所有模型上都正确）。
- **无驱动关节一律命名为 `passive_*`**（轮子、齿隙铰链）。
  所有执行器/观测/奖励选择器都用 `^(?!passive_).*` —— 新增关节时保持前缀约定，而且新的 `passive_` 正则绝不能误匹配齿隙关节（写 `^passive_.*wheel`，不要写 `^passive_.*`）。
- **执行器是 BAM**（电压控制的 XL330 模型，摩擦由执行器计算）。两个后果：任何独立（standalone）环境配置必须注册
  `expand_bam_friction_fields` 启动事件；关节摩擦域随机化必须缩放执行器的 `friction_scale` —— 在 BAM 下 `dof_frictionloss` 被清零，随机化它是无声的空操作。
- **观测归一化是开启的** → 归一化器必须烤进 ONNX。
  `scripts/export.py` 做的就是这件事；在仿真里播放会掩盖这个 bug（它反正会应用归一化器），所以绝不要手工转换检查点。
- **策略是不带滤波的**（训练中不做动作低通）。不要在没有配套运行时开关和迁移测试的情况下加 EMA 滤波 —— 训练时有/部署时没有（任一方向）都会破坏迁移。
- **域随机化绝不能在多次重置之间累积。**mjlab 1.3.0 里 `operation="add"/"scale"` 的 `dr.*` 操作原生不累积（它们重新读取编译期默认值）；自定义 DR 函数必须先恢复再应用。一个会累积的质心（CoM）随机化器曾让每一次长训练持续退化了好几个月。
- 如果某个观测被重映射到传感器视图（齿隙编码器、偏置），对同一个量的任何跟踪类奖励必须度量同一个视图 —— 否则策略会因为纠正它所看到的东西而受罚。
- `-Backlash-` 任务变体必须镜像其基础任务的机器人模型（walk / allcollisions / rollers），这样齿隙 A/B 对比才不受干扰。

## 搭建新环境 —— 工作流程

1. **挑最接近的模板**，在它之上搭建，不要从零开始：
   运动（locomotion）→ velocity 配方；以某个姿势收尾的片段式技巧 → standup；受指令的双态切换 → sitstand；动态机动 → roulade
   （读它的配置 docstring —— 里面编码了 5 次训练的教训轨迹）。基于 `make_microduck_velocity*_env_cfg` 搭建可免费让域随机化/观测/噪声/延迟保持同步；若从 mjlab 的基础模板独立搭建，必须自己移植整套域随机化 + 观测噪声 + NaN 防护栈（grep 一下 velocity 接了什么：`_safe` critic 观测项、带 sensor_names 的 `nan_state` 终止、`expand_bam_friction_fields`、编码器偏置、IMU 失准）。
2. **训练之前先在仿真里验证物理假设** —— 这是单项最大的省时之道：
   - 目标/休息姿势必须是稳定平衡：从带噪声的初始状态保持其 ctrl 3 秒，检查倾角（TILT），而不只是高度（只记录 z 的沉降测试会把摔倒状态报成"休息得很好"）。
   - 在仿真里从实际机器人身上量目标高度（例如站立策略下的躯干 z），绝不跨模型修订沿用。一个差了 5 mm 的 STAND_Z 曾让目标变成好几天都到不了的不可能任务。
3. **配置约定**：配置文件顶部放 `ENABLE_*` 开关 + 调好的常量；工厂函数 `make_..._env_cfg(play: bool, rough: bool)`；在
   `tasks/__init__.py` 注册（适用时加 `_BACKLASH_TASKS` 表）；用带独立 `experiment_name` 的自己的 `RslRl...RunnerCfg`。对称镜像损失（symmetry mirror-loss）可用（61 维表在 `symmetry.py`） —— 默认关闭，且绝不用于非对称任务。
4. **写配置测试**（见 `tests/test_*_cfg.py`）：关节索引在真实模型上可解析、奖励权重符号符合意图、闸门在预期处开/闭。它们在 CPU 上运行并钉死不变量。
5. **冒烟测试**（64 环境、5 迭代）：能构建、步进无 NaN、观测是 61 维、每个奖励项都能算、ONNX 能导出。
6. 训练，盯日志（见下），并预期 2–5 轮"打地鼠"式的奖励投机（reward hacking） —— 这很正常，下面的经验能抄掉大部分近路。

## 奖励设计 —— 每条都是付出过代价才学到的规则

- **符号约定（坑过四个环境）：**mdp.py 有两种惩罚风格。mjlab 基础的代价函数返回 ≥ 0 → 权重为负。自我取反的 microduck 函数（`*_penalty`、`*_l1`，返回 ≤ 0）→ 权重为正。给自我取反的惩罚配负权重，会双重取反变成对违规行为的奖励，策略会去刷它（屁股蹦行、砸坐）。**万无一失的检查：每次运行中，wandb 里每个 `Episode_Reward/<penalty>` 都必须 ≤ 0。**
- **RL 优化的是奖励的字面意思。**每个未充分指定的自由度都会被利用（用弹道甩动代替翻滚、用侧肩滚代替矢状面动作、用头三点支撑代替站立）。把"什么才算这个机动"编码进基于状态的硬闸门（支撑接触、姿态轴检查、锁存器），而不是小惩罚的轻推。
- **不许有头奖（jackpot）：**任何"到达 X"的奖励都必须限速或斜坡化。提前到达一个随后按步付钱的目标状态，是一张能换来自由暴力的头奖。对受指令的转换，跟踪一个斜坡化的内部目标（恒速混合）—— 跑在斜坡前面收益为零，所以慢才是最优解（argmax）。只有速度上限惩罚的话，积分有界、必输。
- **绝不以处于坏状态（摔倒、低矮）作为正奖励的闸门** —— 策略会停在最便宜的合格姿势里刷分。改用基于势函数的整形（potential-based shaping）（付 Δprogress，例如 Δcos(tilt)：升有奖、保持为零、没法刷）。对静态任务，把每个正项对着每一种稳定的趴倒（仰面/俯面/侧面）逐一审计：如果趴倒还能保住奖励栈的大头，策略就会趴倒。
- **片段式落姿任务：**从 t=0 起单一固定目标（对关节和高度用高斯 + L1，std 给宽）+ |a_z| 冲击惩罚 + 两层直立项 —— 不要关键帧/航点轨迹（策略会扎营在航点上）。路径本身才是 RL 应当去发现的东西。
- **正则项分两种。**运动阻断型（body_ang_vel、angular_momentum、pose std）惩罚的是动态动作在物理上必需的东西 —— 动态任务要保持低权重。平滑型（action_rate、joint_torque_rate）抑制抖动而不阻断缓慢的大动作 —— 可以放心加权，但要在技能被发现*之后*再引入（课程从 ~0 起）：在困难技能探索期间生效的任何"尝试税"都会让"什么都不做"获胜。缓慢精细的任务（够取）比行走需要更重的平滑。
- **在环境之间照搬正则项时，比较的是奖励质量（reward mass）而不是权重。**PPO 看的是相对优势：同样的 action_rate 权重，在 4 倍大的正任务栈下弱了 4 倍。
- **跟踪高斯的 std：**约等于你仍然在乎的误差，而不是最大误差 —— 太松在小误差处没有梯度。但在收紧之前，先问这个误差是策略能消除的，还是你想要的行为所固有的（一个占体重 38% 的头在走路时必须振荡；一个紧的瞬时头部跟踪 std 曾把行走罚得策略干脆站着不动）。只给可消除的部分定价 —— 例如对 1 秒 EMA 做 L1，收 DC 偏置的钱、让振荡互相抵消。
- **在目标状态处，乘性组合胜过加性求和：**当加性栈存在一个折中盆地（一个前倾拿到每项的 80%）时，高斯乘积会在任何一个欠缺因子上塌缩 —— 但 std 要选得够宽、让当前策略能拿到肉眼可见的分数，否则梯度不可见、什么都不会变。
- **关节停在硬限位上：**用针对肇事关节的 qpos 侧限位接近度惩罚来修；自带的 `dof_pos_limits` 只在行程最后约 7.5% 触发，而指令侧的惩罚没用（把 ctrlrange 拉宽是有意的 —— 低 kp 舵机需要过冲）。

## 指令、观测与死权重

- **永远为零的指令输入，权重永远是死的。**每个指令槽从第 0 步起就保留一个小的非零采样范围（哪怕奖励权重为 0），这样它的输入神经元才能为后续课程保持活跃。
- **全零指令行为必须显式训练**（`zero_command_prob` 式的精确零采样）：均匀采样几乎不可能产生全零指令，而那恰是部署时的空闲状态。
- 稀有但重要的指令区域需要显式分桶 —— 例如原地转（`rel_turn_in_place_envs`）：独立均匀采样让旋转只占约 2% 的经验，结果永远练不出来。

## 课程（curriculum）

- 步数是环境步：`iteration × 24`（`NUM_STEPS_PER_ENV = 24`）。
- 用验证过的分工：权重日程走 `microduck_mdp.reward_weight`，指令/事件范围走专门的参数课程。`mdp.reward_weight` 是阶跃函数不是插值 —— 把斜坡离散成阶段。
- 通过管理器改词条配置（`env.event_manager.get_term_cfg(...)`），绝不用 `env.cfg.events[...]` —— 管理器在初始化时深拷贝了自己的配置，写 `env.cfg` 是无声的空操作（这也会咬到强制设置生成状态的评估脚本）。
- **让每个阶段与策略实际学到的东西对齐相位**：当前切片巩固之前不要加硬生成混合；技能存在之前不要引入税收。当某个 wandb 指标恰在课程阶段边界处阶跃下降，节奏就错了 —— 拉长阶段或推迟引入，绝不提前。
- 逆向课程生成（reverse-curriculum spawn，让片段从机动的中途开始、包括接近完成的状态）是"学会了开头、永远学不会最后一公里"的可靠解法 —— 否则能力前沿拿不到任何在线（on-policy）数据。

## 训练运维与读曲线

- wandb 项目 `mjlab_microduck`；日志在 `logs/<experiment_name>/`；用 `--agent.load-checkpoint model_XXXX.pt --agent.resume True` 续训。
- 逐迭代盯：平均奖励在升、且片段长度按任务要求表现；每个惩罚项 ≤ 0；主任务项真的在涨（总奖励可以纯粹靠正则项上涨，而技巧从未发生）。`Episode_Reward/<term>` 记录的是加权值 —— 权重为 0 的项无论行为如何都读作 0，所以要对照权重日程解读。
- 预算：简单的片段式技巧在 4096 环境下约 1000 迭代；步态和重课程的恢复任务要 4000–6000。
- **先测量再理论。**当一次训练"失败"，先对实际检查点跑无头评估（按生成类型分组的测试组、终态聚类、角速度剖面）再改奖励：过去的"失败"，有的是检查点太早、有的是成功标准把一个行为簇劈成两半、有的是报酬上限在和实测物理较劲。仿真指标可以全过而视频过不了人眼 —— 看视频，并检查是哪个 geom/轴在接触。
- 汇报 rollout 实际呈现的东西（"能翻滚，但三次里有一次脸着地"），而不是"能跑了！"。够不够好，由用户决定。

## Sim2real 陷阱（每条都花掉过好几周调试）

- 一次干净的 `uv sync` 就是事实标准（HF Jobs 每次都跑一遍）：任何只有靠手动安装的本地包才能跑起来的东西，到了远端就会死。让 `pyproject.toml` 保持诚实。
- **wheel 是分架构的。**在 linux-`aarch64`（DGX Spark / GB10）上，PyPI 的 torch wheel 是 CPU 专用（`2.9.1+cpu`、`torch.version.cuda is None`），于是 `torch.cuda.device_count() == 0`，mjlab 的 `select_gpus()` 对空列表取索引 → 第 0 次迭代之前就 `IndexError`。`[tool.uv.sources]` 仅对 `aarch64` 把 torch 引到 cu129 索引（cu129 与 CUDA 工具包的 warp 包匹配；x86_64/HF Jobs 仍走 PyPI）。两个静默断点都由 `tests/test_aarch64_cuda_torch.py` 锁死：torch 必须保持为直接依赖（uv 的 `[tool.uv.sources]` 只作用于直接依赖 —— 删掉那个看似冗余的 `torch==` 钉会让路由变成空操作），而且钉必须保持 `==`，因为 CUDA 索引带着比 PyPI 更新的构建（一个 `>=` 曾无声地把 torch 从 2.9.1 拖到 2.13.0）。
- 与物理对齐的限值：一台 25 cm 的机器人以 3.5–5.5 rad/s 翻滚是自然的 —— 不要用上限强加人类尺度的速度直觉；把反暴力的压力放在冲击和乱抖上（|a_z|、action_rate、支撑闸门），而不是转速上。
- IMU 域随机化以零为中心 —— 它训练的是对失准幅度的容忍，补偿不了系统性的安装偏置（那是运行时标定的事）。
- 真机部署以共享观测契约热切换 ONNX 策略（walk / stand / trick）—— 碰机器人之前先在 `scripts/infer_policy.py` 里排练，并写对指令槽（一个姿态标志住在 twist 的 vx 槽里；喂全零意味着"站立"，看起来就像"策略不理按钮"）。
