# dance-v1 训练与卡点评估 · 2026-09-02

## 配置
- 任务: dance（DJ 命令注入：head 4 槽 = sin 摇摆 + 节点压头 + 强拍强调）
- 训练: 120 BPM 固定 / 3拍风格 / 3M 步（32 envs, ~14 分钟, M5 Pro）
- 奖励: swing 紧/宽双层 + beat_hit + strong_beat + body_bob + 站立栈

## 结果
- 最终平均 episode reward: **2914**（起点 121, 24 倍）
- 随机动作基线 vs 训练后策略: -177 → +5.9/step 量级

## Held-out BPM 评估（deterministic, 3 episodes/BPM, 1000 步 cap）
| BPM | 节点跟随误差 | 命中率(<0.15rad) | 节点数 |
|---|---|---|---|
| 90（未训过） | 0.273 rad | 31% | 26 |
| 105（训练档） | 0.341 rad | 4% | 26 |
| 140（未训过） | 0.241 rad | 34% | 29 |

## 判读
1. **泛化已现雏形**：未训过的 90/140 BPM 与训练档 105 误差同量级（0.24-0.34rad）
   —— 策略读的是命令槽信号而非背拍，"听什么歌都能跳"的机制成立
2. **绝对精度不够**：0.25-0.34rad ≈ 15-20° 的节点误差 + 105 档命中率异常低，
   说明 swing 主项已学会但 beat_hit 的脉冲时序还没抠细 —— 典型的
   "先学会动，再学会准"。处方（按官方 playbook）：
   - 续训至 6-8M 步（课程后置：此刻收紧 beat 窗口 0.10→0.06）
   - beat_hit 权重 2.0→3.0，strong_beat 1.5→2.5
   - 加入 DANCE_PHASE 随机（当前固定 0），防 memorize 相位
3. 命中率 105 档反低的疑似原因：训练正处 reward-hacking 迁移期（策略还在
   摇摆与打点间折中），需 per-term 曲线确认（wandb/tensorboard）

## 产物
- runs/dance-v1/policy.onnx + bpm_eval.json
- 训练日志 /tmp/dance_train.log
