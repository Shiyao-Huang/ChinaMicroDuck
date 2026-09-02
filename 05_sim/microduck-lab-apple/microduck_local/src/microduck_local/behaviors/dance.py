"""Dance — 卡点舞：跟随 DJ 写进 head 命令槽的节拍信号。

核心思想（用户 2026-09-02 洞察）：卡点不需要听歌——DJ 放什么歌
（BPM/风格/相位）节拍就定了。训练时每次 reset 随机 BPM+风格+相位，
策略学的是「读命令槽里的节拍信号并让身体跟上」，不是背一段固定舞。
上真机后：节拍检测器（librosa onset beat）写同一个 head_cmd 槽，
同一策略对任何歌卡点。

注意：BehaviorEnv 的 commands 被钉在零附近 + keep-alive 噪声，
但 head_cmd 在 DanceEnv.step 里每步被 DJ 重写——这是"活"的节拍通道。
"""
from .core import *  # noqa: F401,F403

import numpy as np

from .. import contract as C


def _beat_terms(env) -> tuple[float, float, float, float]:
    """从 head 命令槽反推 DJ 目标（命令槽 = 乐谱）。
    返回 (swing_target, pulse_target, phase01, strong)。"""
    neck_t = float(env.head_cmd[0])            # sin 摇摆目标
    pulse_t = float(env.head_cmd[1])           # -amp 打点目标（非节点=0）
    bps = float(os.environ.get("DANCE_BPM", "105")) / 60.0
    phase01 = (bps * env.data.time) % 1.0
    bpb = 3.0 if os.environ.get("DANCE_STYLE", "four4") == "three4" else 4.0
    strong = (np.floor(bps * env.data.time) % bpb) == 0.0
    return neck_t, pulse_t, phase01, strong


def _swing_track(env) -> float:
    """主奖励：neck_pitch 实际角贴合 sin 摇摆目标（紧层 std 0.12）。"""
    neck_t = float(env.head_cmd[0])
    actual = float(env._joint_pos_rel()[5])    # neck_pitch
    err = actual - neck_t
    return float(np.exp(-(err * err) / 0.12 ** 2))


def _swing_track_wide(env) -> float:
    """宽层（std 0.4）：探索期唯一梯度来源。"""
    neck_t = float(env.head_cmd[0])
    actual = float(env._joint_pos_rel()[5])
    err = actual - neck_t
    return float(np.exp(-(err * err) / 0.4 ** 2))


def _beat_hit(env) -> float:
    """节点命中：窗口内贴脉冲目标；窗口外必须回 0（v5 教训：无回位奖励时
    策略把头停在 -0.3 不回——严格命中率只剩 30%）。全时段有梯度。"""
    _, pulse_t, _, _ = _beat_terms(env)
    actual = float(env._joint_pos_rel()[6])    # head_pitch
    err = actual - pulse_t
    inside = float(np.exp(-(err * err) / 0.3 ** 2))
    if pulse_t >= 0.0:                          # 窗口外：目标是 0（回位）
        home_err = actual - 0.0
        return 0.10 * float(np.exp(-(home_err * home_err) / 0.15 ** 2))
    return inside


def _beat_hit_strong(env) -> float:
    """强拍加倍：bar 首拍的命中分 ×2 语义（独立项，方便 wandb 看）。"""
    _, pulse_t, _, strong = _beat_terms(env)
    if not strong or pulse_t >= 0.0:
        return 0.0
    actual = float(env._joint_pos_rel()[6])
    err = actual - pulse_t
    return float(np.exp(-(err * err) / 0.3 ** 2))


def _dip_park_pen(env) -> float:
    """v4 教训：策略把 head_pitch 压在 +1.22 rad 限位躺赢（官方 playbook
    'Joints parking on hard limits' 条目）。qpos 侧限位接近惩罚。"""
    hp = float(env._joint_pos_rel()[6])
    return -float(max(0.0, abs(hp) - 0.9)) * 2.0


def _bob_with_beat(env) -> float:
    """身体律动：躯干 z 在节点处有小幅弹性起伏（卡点不只靠头）。
    用躯干线速度 z 与拍相位的相关性——节点下压瞬间 bz<0（下沉）。"""
    _, pulse_t, phase01, _ = _beat_terms(env)
    bz = float(env.body_lin_vel()[2])
    if pulse_t < 0.0 and phase01 < 0.15:
        return float(np.clip(-bz / 0.05, 0.0, 1.0))  # 下沉得分
    if 0.3 < phase01 < 0.6:
        return float(np.clip(bz / 0.05, 0.0, 1.0))   # 回弹得分
    return 0.1


_register(Behavior(
    id="dance",
    emoji="🕺",
    title="Dance to the beat",
    description=(
        "Follow the beat signal the DJ streams into the head command slots: "
        "swing the neck with the sine, dip the head on each beat pulse, "
        "emphasize the strong beat, and let the body bob. Works at any BPM "
        "the DJ plays because the beat rides the observation, not memory."
    ),
    how_it_learns=(
        "At first the duck ignores the command slots — the wide swing layer "
        "pays a little for any neck motion in the right direction. As its "
        "neck lands on the sine target, the tight layer pays big. Beat pulses "
        "pay only when head pitch actually dips inside the pulse window, and "
        "the bar's first beat pays double. Legs keep the standing stack; "
        "extra body bob earns a bonus. Train with DANCE=1 so the DJ env is "
        "mounted and every reset rolls a new BPM/style/phase."
    ),
    keywords=("dance", "卡点", "beat", "music", "disco", "freestyle"),
    terms=(
        RewardTerm("swing_tight", "Big points for neck matching the beat sine", 2.5, _swing_track),
        RewardTerm("swing_wide", "Wide layer so exploration finds the groove", 1.2, _swing_track_wide),
        RewardTerm("beat_hit", "Points for dipping the head inside the beat pulse", 3.0, _beat_hit),
        RewardTerm("strong_beat", "Double dip on the bar's first beat", 1.5, _beat_hit_strong),
        RewardTerm("body_bob", "Points for body bounce synced to beats", 0.8, _bob_with_beat),
        _upright_term(1.5),
        RewardTerm("legs_planted", "Keep both feet down — dance on the spot", 0.8,
                   lambda env: _both_feet_down(env)),
        RewardTerm("stay_home", "Penalty for wandering", 1.2, _stay_home_pen, is_penalty=True),
        RewardTerm("calm_body", "Penalty for thrash", 1.0, _still_body_pen, is_penalty=True),
        RewardTerm("dip_park", "Penalty for parking head pitch on its limit", 1.5,
                   _dip_park_pen, is_penalty=False),
        RewardTerm("smooth_moves", "Light smoothness — grooving is motion", 0.6,
                   _action_rate_pen, is_penalty=True),
    ),
    default_steps=3_000_000,
    # v1/v2 后验：会跟拍但 ~1.4s 就摔 —— 与 official backflip 的"先学站稳"同坑。
    # 课程三段：微摆站稳 → 半幅跟拍 → 全幅卡点（DANCE_SWING/DANCE_DUTY 走 spawn knob）。
    curriculum=(
        CurriculumStage("learn to stand with a tiny groove", 1_500_000,
                        {"DANCE_SWING": "0.08", "DANCE_DUTY": "0.0",
                         "MICRODUCK_EPISODE_S": "10"},
                        detail=(
                            "Beat signal at quarter amplitude, no beat pulses: "
                            "the duck's only job is to stay upright while the "
                            "head target sways gently. Stand first, then dance.")),
        CurriculumStage("half-amplitude groove", 1_500_000,
                        {"DANCE_SWING": "0.15", "DANCE_DUTY": "0.05",
                         "MICRODUCK_EPISODE_S": "14"},
                        detail=(
                            "Half swing, soft beat pulses. Tracking tightens "
                            "while the balance stack holds the line.")),
        CurriculumStage("full-amplitude on-beat dancing", 3_000_000,
                        {},
                        detail=(
                            "Full swing + beat pulses + strong-beat emphasis "
                            "at 120 BPM — the whole trick, now on a body that "
                            "knows how to stand.")),
    ),
    success_metric="beat-hit rate + swing tracking error at held-out BPMs",
    episode_s=24.0,
    symmetric=False,  # 卡点舞无镜像对称（强拍有方向性）
))
