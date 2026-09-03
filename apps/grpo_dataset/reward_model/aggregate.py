from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AggregateInputs:
    executability: float
    alignment_keyword: float
    alignment_clip: float
    coverage: float
    vcer_penalty: float


@dataclass
class AggregateWeights:
    executability_gate: float
    alignment_keyword: float
    alignment_clip: float
    coverage: float
    vcer_penalty: float


@dataclass
class AggregateResult:
    reward: float
    breakdown: dict[str, float]


def aggregate_reward(inputs: AggregateInputs, weights: AggregateWeights) -> AggregateResult:
    if inputs.executability < weights.executability_gate:
        return AggregateResult(
            reward=0.0,
            breakdown={
                "executability": inputs.executability,
                "alignment_keyword": inputs.alignment_keyword,
                "alignment_clip": inputs.alignment_clip,
                "coverage": inputs.coverage,
                "vcer_penalty": inputs.vcer_penalty,
                "final_reward": 0.0,
            },
        )

    alignment = (
        weights.alignment_keyword * inputs.alignment_keyword
        + weights.alignment_clip * inputs.alignment_clip
    )
    reward = alignment + (weights.coverage * inputs.coverage) - (weights.vcer_penalty * inputs.vcer_penalty)
    reward = max(0.0, min(1.0, reward))

    return AggregateResult(
        reward=reward,
        breakdown={
            "executability": inputs.executability,
            "alignment": alignment,
            "coverage": inputs.coverage,
            "vcer_penalty": inputs.vcer_penalty,
            "final_reward": reward,
        },
    )
