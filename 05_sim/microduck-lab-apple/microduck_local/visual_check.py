"""视觉验证：用训练好的 dance 策略 rollout 并逐帧渲染成 contact sheet。

输出:
  runs/<name>/visual_frames/  每隔 N 控制步一张 PNG（覆盖整拍周期）
  runs/<name>/visual_report.json  逐帧: beat_phase, neck 实际 vs 目标, head dip

判据（视觉可读）:
  - strong beat 帧: head_pitch 应明显下压（负值）
  - swing 应呈正弦包络: 帧序列 neck 角有连续大摆动
用法:
  uv run python ../../visual_check.py runs/dance-v2 105
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, "src")
os.environ.setdefault("DANCE_STYLE", "four4")


def main(run_dir: str, bpm: int = 105):
    os.environ["DANCE_BPM"] = str(bpm)
    from stable_baselines3 import PPO

    from microduck_local.behaviors.dance_env import DanceEnv

    model = PPO.load(os.path.join(run_dir, "model.zip"))
    env = DanceEnv("dance")
    obs, _ = env.reset()

    import mujoco

    frames_dir = os.path.join(run_dir, "visual_frames")
    os.makedirs(frames_dir, exist_ok=True)
    renderer = mujoco.Renderer(env.model, height=480, width=640)

    report = []
    CAPTURE_EVERY = 25          # 每 0.5s 一帧
    total_steps = int(24.0 / 0.02)  # 一个 episode 24s
    obs_t = obs
    done = False
    step = 0
    while not done and step < total_steps:
        action, _ = model.predict(obs_t, deterministic=True)
        obs_t, r, term, trunc, info = env.step(action)
        done = term or trunc
        if step % CAPTURE_EVERY == 0:
            renderer.update_scene(env.data, camera=-1)
            img = renderer.render()
            import PIL.Image

            PIL.Image.fromarray(img).save(
                os.path.join(frames_dir, f"f{step:05d}.png"))
            bps = bpm / 60.0
            phase = (env.data.time * bps) % 1.0
            strong = (np.floor(env.data.time * bps) % 4) == 0
            report.append(dict(
                step=step, t=round(env.data.time, 2),
                beat_phase=round(phase, 3), strong=bool(strong),
                neck_actual=round(float(env._joint_pos_rel()[5]), 3),
                neck_target=round(float(env.head_cmd[0]), 3),
                headpitch_actual=round(float(env._joint_pos_rel()[6]), 3),
                headpitch_target=round(float(env.head_cmd[1]), 3),
            ))
        step += 1

    json.dump(report, open(os.path.join(run_dir, "visual_report.json"), "w"),
              indent=1)
    # 摘要: 节点帧的下压幅度 & swing 幅度
    dips = [f["headpitch_actual"] for f in report if f["beat_phase"] < 0.15]
    swings = [abs(f["neck_actual"]) for f in report]
    print(f"frames: {len(report)}  saved-> {frames_dir}")
    print(f"beat-window head dip: mean={np.mean(dips):.3f} min={min(dips):.3f}"
          f"  (负值越大=点头越深)")
    print(f"neck swing range: {min(swings):.3f}..{max(swings):.3f} rad")
    ok = min(dips) < -0.2 and max(swings) > 0.25
    print("VISUAL CHECK:", "PASS" if ok else "WEAK — 需要更多训练")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 105)
