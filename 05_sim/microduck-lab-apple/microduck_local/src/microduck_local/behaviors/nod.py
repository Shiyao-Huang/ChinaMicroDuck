"""Nod — 原地连续点头：head_pitch 在下压位与 HOME 位之间往复，躯干稳定站立。

新能力配方示范（第 10 页 wiki 的实战版）。设计遵守 AGENTS.md 三条铁律：
- 节律目标用 sin 相位跟踪（连续，无 jackpot）
- 平滑惩罚权重低（动态动作不能在探索期收税）
- 双层 tracking：宽层(std 0.5)先给梯度，紧层(std 0.15)收尾精度
"""
from .core import *  # noqa: F401,F403

import numpy as np

# nod 目标幅度：head_pitch 在 HOME(0.3491) 基础上 ±0.45 rad（≈±26°）
_NOD_AMP = 0.45
_NOD_PERIOD_S = 1.2  # 一个完整点头周期


def _nod_target(t: float) -> float:
    """时刻 t 的目标 head_pitch 偏移（相对 HOME），平滑 sin 轨迹。"""
    return _NOD_AMP * np.sin(2.0 * np.pi * t / _NOD_PERIOD_S)


def _nod_track(env) -> float:
    """主奖励：head_pitch 实际偏移 vs sin 目标的高斯跟踪。
    双层中的紧层——std 0.15 rad ≈ 8.6°，只对最后几度付满分。"""
    t = float(env.data.time)
    target = _nod_target(t)
    actual = float(env._joint_pos_rel()[6])  # idx 6 = head_pitch
    err = actual - target
    return float(np.exp(-(err * err) / 0.15 ** 2))


def _nod_track_wide(env) -> float:
    """宽层（std 0.5 rad）：探索期唯一的梯度来源——紧层在误差大时付 exp(-∞)≈0。"""
    t = float(env.data.time)
    target = _nod_target(t)
    actual = float(env._joint_pos_rel()[6])
    err = actual - target
    return float(np.exp(-(err * err) / 0.5 ** 2))


def _nod_amplitude(env) -> float:
    """幅度层：实际偏移的 |sin| 一致性——鼓励摆到目标幅度而不是原地小抖。
    L1 于 1s EMA（官方技巧：只罚 DC 偏置，让振荡自由通过）。"""
    actual = float(env._joint_pos_rel()[6])
    t = float(env.data.time)
    # 1 秒滑动平均近似 DC 分量；sin 周期 1.2s，EMA≈0 对振荡项公平
    if not hasattr(env, "_nod_ema"):
        env._nod_ema = 0.0
    env._nod_ema += 0.02 * (actual - env._nod_ema)
    return float(np.exp(-abs(env._nod_ema) / 0.1))


_register(Behavior(
    id="nod",
    emoji="🙏",
    title="Nod the head",
    description=(
        "Stand still and nod the head rhythmically: head pitch swings down "
        "and back to home at about one nod per 1.2 s, legs planted, body calm."
    ),
    how_it_learns=(
        "The duck first gets wide-gradient points for moving head pitch at all "
        "(tight tracking pays zero when the error is huge). As the swing gets "
        "close to the sin target, the tight layer takes over and pays for "
        "rhythmic precision. Legs and body are held by the standing stack; "
        "thrash costs points."
    ),
    keywords=("nod", "nod head", "点头", "bow head", "yes yes"),
    terms=(
        RewardTerm("nod_track", "Big points for head pitch matching the sin target tightly", 3.0, _nod_track),
        RewardTerm("nod_wide", "Wide-gradient layer so exploration can find the swing", 1.5, _nod_track_wide),
        RewardTerm("nod_amplitude", "Points for keeping the DC drift near zero (real swing, not lean)", 0.8, _nod_amplitude),
        _upright_term(1.5),
        RewardTerm("head_else_still", "Points for keeping OTHER head joints (yaw/roll) quiet", 0.6,
                   lambda env: float(np.exp(-float((env._joint_pos_rel()[[7, 8]] ** 2).sum()) / 0.1 ** 2))),
        RewardTerm("legs_planted", "Points for keeping both feet on the floor", 0.8,
                   lambda env: _both_feet_down(env)),
        RewardTerm("stay_home", "Penalty for wandering away", 1.0, _stay_home_pen, is_penalty=True),
        RewardTerm("calm_body", "Penalty for body thrash", 1.0, _still_body_pen, is_penalty=True),
        RewardTerm("smooth_moves", "Penalty for jerky motion (low: discovery first)", 0.8,
                   _action_rate_pen, is_penalty=True),
        RewardTerm("gentle_joints", "Penalty for joint flailing (low: nod IS motion)", 1.0,
                   _joint_vel_pen, is_penalty=True),
    ),
    default_steps=2_000_000,
    success_metric="mean nod tracking error per episode",
    episode_s=20.0,
    symmetric=False,  # 单方向点头，镜像会拉扯配方
))
