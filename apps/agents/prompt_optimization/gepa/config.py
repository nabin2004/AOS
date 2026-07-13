from dataclasses import dataclass
from typing import Literal


@dataclass
class GEPAConfig:
    """Configuration for one dspy.GEPA prompt optimization run."""

    task_model: str = "openrouter/google/gemini-2.5-flash-lite"
    reflection_model: str = "openrouter/google/gemini-2.5-flash-lite"

    # Budget — exactly one of these is passed to dspy.GEPA.
    auto: Literal["light", "medium", "heavy"] | None = "light"
    max_full_evals: int | None = None
    max_metric_calls: int | None = None

    reflection_minibatch_size: int = 3
    candidate_selection_strategy: Literal["pareto", "current_best"] = "pareto"
    use_merge: bool = True
    max_merge_invocations: int | None = 5
    num_threads: int | None = None
    track_stats: bool = True
    seed: int | None = 0

    trainset_path: str = "apps/agents/prompt_optimization/datasets/train.jsonl"
    valset_path: str = "apps/agents/prompt_optimization/datasets/dev.jsonl"
    output_dir: str = "apps/agents/prompt_optimization/reports"
    log_dir: str | None = None
