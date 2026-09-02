"""DanceEnv — DJ 命令注入环境。

用户的洞察：**卡点不需要听歌，DJ 放什么歌就定义了节拍**。
训练时随机 BPM/风格/相位偏移 = 无穷多"歌"，策略学会的是
「跟上 head_cmd 槽里给的节拍信号」——上真机后同一策略对任何
BPM 都能卡点（运行时只需要一个节拍检测器写同一个槽）。

接线（零改动框架，全部走已有机制）：
- 命令注入: 子类 step() 覆写 head_cmd —— resample 被禁用防覆盖
- 训练多样性: os.environ 读 DANCE_BPM/DANCE_STYLE/DANCE_PHASE
  （train_behavior 已把进程环境传给子进程；env 由 trainer 构造）

节拍语义（编舞协议，正拍=strong beat）:
- 4/4:  每拍 0/-1 交替（odd beat 下压）
- 3/3(3拍): 每 3 拍一个 strong，其余弱
- 摇滚(rock): 2/4 强拍 + 头部重协议幅度 ×1.3

头部动作协议（head_cmd 4 槽 = neck_pitch/head_pitch/head_yaw/head_roll）:
- neck_pitch  = A·sin(2πft + φ)         摇摆（每个 head 命令槽都有 head-err 高斯跟踪奖励在等）
- head_pitch  = -B·pulse(beat)          下压打点（beat 相位 < duty 时压下）
- head_yaw    = C·square(beat, style)   4/4 时左右甩头
- 可选: hip bob 由 body_cmd z 槽承载（这里不用，保持腿任务简单）
"""
from __future__ import annotations

import os

import numpy as np

from .env import BehaviorEnv


class DanceEnv(BehaviorEnv):
    """节拍由 DJ（本类）写进 head 命令槽的舞蹈训练环境。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bpm = float(os.environ.get("DANCE_BPM", "105"))
        self.style = os.environ.get("DANCE_STYLE", "four4")
        self.phase0 = float(os.environ.get("DANCE_PHASE", "0"))
        self.swing_amp = float(os.environ.get("DANCE_SWING", "0.30"))
        self.duty = float(os.environ.get("DANCE_DUTY", "0.10"))
        if self.style == "rock":
            self.swing_amp *= 1.3
        self.beats_per_bar = 3.0 if self.style == "three4" else 4.0

    def step(self, action):
        t = self.data.time
        bps = self.bpm / 60.0
        # --- 头部摇摆：连续 sin，命令槽 51 (neck_pitch)
        self.head_cmd[0] = self.swing_amp * np.sin(2 * np.pi * bps * t + self.phase0)
        # --- 打点脉冲：节点压头 head_pitch（槽 52）
        beat_phase = (bps * t + self.phase0 / (2 * np.pi)) % 1.0
        strong = (np.floor(bps * t + self.phase0 / (2 * np.pi)) %
                  self.beats_per_bar) == 0.0
        amp = 0.45 if (self.style == "rock" and strong) else 0.30
        self.head_cmd[1] = -amp if beat_phase < self.duty else 0.0
        # --- 4/4 甩头：head_yaw 方波（槽 53），3 拍风格不加
        if self.style == "four4":
            self.head_cmd[2] = 0.20 * np.sign(np.sin(np.pi * bps * t))
        # --- 强拍侧倾：head_roll 一点视觉强调（槽 54）
        self.head_cmd[3] = 0.06 if (strong and beat_phase < 0.15) else 0.0
        return super().step(action)

    def _sample_commands(self) -> None:
        pass  # DJ 接管——随机采样会覆盖节拍
