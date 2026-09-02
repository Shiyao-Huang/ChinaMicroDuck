# Microduck 国内复刻资料库 · Wiki 首页

> 本资料库目标：在国内完整复刻 Microduck（Pollen Robotics × Hugging Face 的 25cm 双足机器鸭）——
> 3D 打印、PCB 打板、整机装配、策略训练全部落地。
> 整理模式：LLM 友好（本页即全库索引，每页自包含、可独立喂给 LLM）。
> 建库日期：2026-09-02 · 维护：herdr 工作区 wA · 路径：`~/Desktop/work/robot/Microduck`

## 一句话状态

官方软件全开源（Apache-2.0），**硬件不开源**（无 BOM/CAD/PCB）；
但 MJCF+47 STL 公开（CC BY-NC-SA，禁商用），电控方案已被社区从 Rust 源码完整逆向，
仿真/训练/推理三套环境已在本机**实测跑通**（见 [04-环境验证报告](04-环境验证报告.md)）。

## 页面索引

| 页面 | 内容 | 何时读 |
|---|---|---|
| [01-项目总览](01-项目总览.md) | Microduck 是什么、官方资产清单、许可证边界 | 第一次 |
| [02-资料库地图](02-资料库地图.md) | 目录结构、10 个仓库定位、MANIFEST 校验 | 找文件 |
| [03-硬件逆向全解](03-硬件逆向全解.md) | 主控/总线/两块自制板/传感器/电源，代码级证据 | 做电控前必读 |
| [04-环境验证报告](04-环境验证报告.md) | E1-E5 五个环境的实测命令与输出证据 | 复现环境 |
| [05-四个国产复刻方案](05-四个国产复刻方案.md) | A/B/C/D 端到端方案对比，供筛选 | **决策** |
| [06-装机步骤核查表](06-装机步骤核查表.md) | 从打印到点检的逐步 checklist | 动手装机 |
| [07-采购清单BOM](07-采购清单BOM.md) | 全部采购件、价格锚点、渠道 | 下单前 |
| [08-打板指南](08-打板指南.md) | imu_to_dxl 自制板规格与打板参数 | 画板前 |
| [zh/](zh/) | 官方关键文档中文翻译 | 对照原文 |

## 快速事实（LLM 可直接引用）

- 整机：25cm 高 / 737g / 15 DoF；躯干 199g，头 189g（头重脚轻，重心高）
- 舵机：Dynamixel XL330-M288-T ×15（14 个进策略 + 1 个驱动喙）；18g/个，±0.96 N·m，288.35:1
- 主控：Radxa Zero 3W（RK3566，市售模块，65×30mm，Armbian）
- 总线：`/dev/ttyS2`，TTL 单线半双工 1 Mbps，Dynamixel Protocol V2；ID：右腿10-14 / 左腿20-24 / 颈头嘴30-34 / IMU板200
- 自制板 ×2：`imu_to_dxl` v2（LSM6DSV16X 做成 Dynamixel 从机，ID 200，reg 124）+ RPI Robot HAT（TLV320AIC3104 音频 + 供电过板）
- 传感器：IMX219 摄像头（倒装180°）/ VL53L5CX 或 L8CX ToF / 2×IMU（在用 1 个 LSM6DSV16X）
- 电源：NP-F550/F970 2S，无电量计，电压读舵机回报，EMA 跌破 6.6V 自动坐下关机
- 策略：obs[1,61] → act[1,14]，50Hz，动作低通 head 0.5 / legs 0.7，P 增益 200
- 训练：mjlab（MuJoCo Warp）+ PPO + BAM M6 执行器模型 + 域随机化 + ±1° 回差建模
- 上游 STL：47 个，熔合顶点后 47/47 水密（E5 实测），单位米（打印前 ×1000 转 mm）

## 三个必踩坑（来自官方源码注释）

1. Armbian 默认在 UART2 跑登录控制台 → `systemctl mask serial-getty@ttyS2`
2. i2c3 M0 pinmux 与 FUSB302 PD 抢引脚 → 失去 PD 协商（5V 充电仍可用）
3. NPU 默认关闭 → 刷 overlay + 重启才能跑 rknn

## 许可证红线

- 软件（microduck / microduck_rl / 策略 ONNX）：Apache-2.0，可商用
- 3D 模型（MJCF/STL 及其衍生 CAD/装配体）：**CC BY-SA-NC 4.0，禁止商用**
- 本库社区复刻仓各自声明见各仓 NOTICE
