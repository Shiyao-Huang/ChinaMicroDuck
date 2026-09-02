# gait-v1 训练结果 · 2026-09-02

## 配置
- 任务: train-walk（速度指令步态, CPU MuJoCo + SB3 PPO, BAM 执行器）
- 规模: 32 envs × 3,000,000 steps（~12 分钟, M5 Pro 48GB）
- 契约: obs[1,61] → actions[1,14], 归一化器烤进 ONNX
- checkpoints: 500k / 1M / 1.5M / 2M / 2.5M / 3M

## 评估（eval-walk, 20 episodes @ 1000 步）
```
falls: 0/20 (0%)
lin vel tracking err: mean 0.220 m/s (p90 0.390)
ang vel tracking err: mean 0.440 rad/s (p90 0.919)
```

## 结论
- **不摔**：20/20 episodes 全程站立 —— 基础步态已成立
- 速度跟踪 0.22 m/s 误差偏大 = 3M 步只是起步量；官方同任务在 4096 envs CUDA 上
  跑 3-4 倍数据量才到可用精度。继续训（或上 64 envs + 6M 步）预期显著收敛
- 下一步选项：
  1. `--envs 64 --steps 6_000_000` 续训（从 checkpoint resume）
  2. `-Backlash-` 变体（±1° 齿轮间隙）训一版，对照抗回差鲁棒性
  3. `infer_policy.py` 加载本 ONNX 彩排手柄指令（↑↓←→ A/E）
