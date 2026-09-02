# imu_to_dxl v2 · 自制板设计规格书（打板输入）

> 官方硬件不开源（无原理图/Gerber）。本规格从官方 Rust 运行时源码完整逆向，
> 满足它即可与官方主控软件无缝协作。目标：KiCad/立创EDA 画板 → 嘉立创打样。
> 许可：本规格为独立逆向成果整理；机器人其余 3D 资产 CC BY-NC-SA 禁商用。

## 1. 功能定义

把 LSM6DSV16X IMU 封装成 **Dynamixel Protocol V2 从机**，挂在舵机 TTL 总线上，
与 15 个 XL330 在同一次 sync_read 事务中被主控读出。主控零改动。

## 2. 总线契约（必须逐条满足）

| 项 | 值 | 来源 |
|---|---|---|
| 电气 | TTL 单线半双工，3.3V，3 线（DATA/VDD/GND） | XL330 规格 |
| 速率 | 1 Mbps（与舵机同总线） | robotd.toml |
| 协议 | Dynamixel Protocol V2（含 CRC16-CCITT） | bus.rs |
| 设备 ID | **200**（EEPROM 区，可写改） | ids 列表 |
| 数据寄存器起始 | **124**（RAM 区） | bus.rs sync_read 124..136 |
| 控制环读长 | 12 字节（124–135） | 同上 |
| 诊断块 | 20 字节（另含原始加速度/采样计数/状态标志） | 完整读取路径 |
| 响应时序 | 须在总线轮询窗口内完成（50Hz tick，~10ms 预算，与 15 舵机共享） | 50Hz 环 |

### 12 字节布局（reg 124 起）

| 偏移 | 内容 | 格式 |
|---|---|---|
| 0–5 | gyro x/y/z | i16 小端 ×3，量程 ±500 dps，17.5 mdps/LSB |
| 6–11 | SFLP 四元数 x/y/z | IEEE fp16 ×3；w = √(1−x²−y²−z²)（主控自算） |

## 3. 器件选型（BOM）

| 器件 | 推荐 | 备选 | 备注 |
|---|---|---|---|
| IMU | LSM6DSV16X（LGA-12） | 引脚兼容 ST 6 轴 | 必须——SFLP 硬件融合出游戏旋转四元数 + 陀螺零偏估计 |
| MCU | STM32G030K8 | STM32G431 / CH32V203 / ESP32-C3 | 需 1Mbps UART + DMA、SPI 或 I2C 主、32KB flash 够 |
| 总线收发 | 半双工方向自动切换电路 | 74HC125/126 三态组 + RC | 官方无方向 GPIO → 硬件自动方向；或专用 1-wire 半双工收发 |
| 电源 | 总线取电 5V→3.3V LDO | XC6206/ME6211 | 注意舵机总线 VDD 实际是电池 7.4V！→ 用 8V 耐压 LDO 或 串小降压 |
| 连接器 | JST-PH 3-pin ×2（in/out 菊花链） | | 与 XL330 同款 |
| 被动 | 100nF×2 + 4.7µF 去耦 | | |

> ⚠️ 供电注意：Dynamixel 总线 VDD = 电池电压（6.6–8.2V），不是 5V。LDO 输入耐压 ≥10V。
> ⚠️ 半双工时序：TX 使能由发送数据沿触发（RC 延迟保持），标准 Dynamixel 从机电路，
> ROBOTIS e-Manual 有参考；CH32V203 方案可直接抄开源 Dynamixel 从机固件（如
> 飞特/幻尔的串行舵机从机实现反推）。

## 4. 固件要点

1. UART 1Mbps + IDLE 中断/DMA 收包 → CRC 校验 → 功能分发（PING/READ/SYNC_READ 应答）
2. SPI 8MHz 读 LSM6DSV16X（推荐 SPI，I2C 400kHz 也够但抖动大），
   ODR ≥ 200Hz，FIFO 开 SFLP game rotation + gyro
3. 打包：gyro i16（±500dps 量程缩放 17.5mdps/LSB）、四元数 fp16（fp32→half 舍入）
4. 环形缓存最新样本，SYNC_READ 到达即回，**绝不在中断里做浮点重活**
5. 采样计数器 + 状态标志放诊断区（reg 136+）

## 5. 打板参数（嘉立创经济板）

| 项 | 值 |
|---|---|
| 层数 | 2 层 |
| 尺寸 | ≤ 20×15mm（装进躯干预留位；以实机测绘为准） |
| 板厚 | 1.0mm（轻） |
| 最小线宽/孔 | JLCC 经济款默认（5/5mil 无需加价） |
| 表面处理 | HASL（打样） |
| 安装 | M2 ×2 孔位随机体设计 |
| 数量 | 5 片起（含失败冗余） |

## 6. 验证流程（板回来后）

1. USB 转 TTL + robofriend/铁心 Dynamixel 工具：PING ID200 → READ 124 长 12 → 数据跳动合理
2. 静置：gyro ≈ 0（零偏内），四元数 ≈ 单位
3. 手转 90°：四元数跟随，w 分量回算正确
4. 挂真总线（15 舵机 + 本板）：官方 `robotd` 起动，`robotctl` 查看 IMU 流 50Hz 稳定
5. 对比测试：与 LSM6DSV16X 评估板并排，同一扰动下姿态差 < 2°

## 7. HAT 板（可选，可省）

官方 HAT（65×30mm）= TLV320AIC3104 音频 + 供电过板 + Stemma ToF 口 +（休眠 BMI088）。
**复刻可拆**：
- 不要麦克风/喇叭 → 完全省略，用 USB-C 5V 直接供主控
- 要音频 → MAX98357A（I2S 放麦）模块 + USB 麦克风替代，不画板
- ToF → VL53L8CX 成品模块 4 线直插 pin3/5（I2C3）
- 半双工自动方向电路（舵机总线）→ 若不做 HAT，并入 imu_to_dxl 板或独立小转接板
