#!/bin/zsh
# E1 一键复现：官方行走策略 + MuJoCo 本机 50Hz 实跑
# 用法: zsh 05_sim/run_e1_sim.sh   （viewer 窗口打开后：↑加速 A/E转向 Space清零 T暂停 Q退出）
set -e
ROOT="/Users/copizzah/Desktop/work/robot/Microduck"
PY="$ROOT/05_sim/.venv/bin"

if [ ! -x "$PY/mjpython" ]; then
  echo "==> 建 E1 环境"
  uv venv --python 3.12 "$ROOT/05_sim/.venv"
  uv pip install --python "$PY/python" mujoco onnxruntime numpy better-actuator-models
fi

cd "$ROOT/01_official/microduck_rl"
exec "$PY/mjpython" scripts/infer_policy.py \
  --walking "$ROOT/01_official/microduck-policies/alpha_walking.onnx" \
  --new-cmd-obs --debug
