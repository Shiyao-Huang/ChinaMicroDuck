# dance-v6b 终版验收 · 2026-09-02

## 95% 达标验收（policy.onnx，归一化器内嵌，deterministic）

| BPM | 存活(4ep) | 摔 | neck跟拍误差 | 窗口命中率 |
|---|---|---|---|---|
| 90（区间随机内）| 24s×4 | 0 | 0.024 rad | **98.67%** ✅ |
| 105 | 24s×4 | 0 | 0.017 rad | **99.25%** ✅ |
| 120 | 24s×4 | 0 | 0.016 rad | **99.35%** ✅ |
| 140 | 24s×4 | 0 | 0.020 rad | **99.81%** ✅ |

训练配置：BPM 每 episode 随机 90-140（真·多歌域随机化）+ 回位奖励(0.10 系数)
+ 从 v5 热启动 + 3M 步。视觉帧：runs/dance-v6b/visual_frames/ 60 帧 @140BPM。

## v6 失败复盘（1 行）
回位奖励系数 0.25 导致奖励尺度突变 → PG loss 转正 → 策略崩溃（0.2s 摔）。
系数降到 0.10 后稳定收敛。教训：奖励改动要小步走。

## 归档
- 05_sim/final_policies/dance-beat-99percent.onnx (sha256 570d0a40…fbfae)
- 05_sim/final_policies/nod.onnx (sha256 5ac1c0ef…74c14a)
- 契约 obs[1,61]→act[1,14]，官方 runtime 可直接热加载
