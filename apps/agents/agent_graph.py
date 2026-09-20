"""Animus Agent Graph — Declarative Pipeline Facade for Educational Animations.

This module exposes the backward-compatible interface for the modular
`animation_pipeline` package. For class-based design and direct OOP integration,
import from `animation_pipeline`.
"""

from __future__ import annotations

import asyncio
import sys

from animation_pipeline import (
    AnimationGraphBuilder,
    AnimationPipelineAgent,
    AnimationPipelineRunner,
    AnimationState,
    BaseAnimationNode,
    ClassifyNode,
    CodeAgent,
    CodeAgentNode,
    PipelineArtifactManager,
    PipelineResult,
    PlanLectureNode,
    PlanTeachingScriptNode,
    animation_agent,
    animation_graph,
    run_coder_step,
    run_pipeline,
    subject_str,
)

__all__ = [
    "AnimationState",
    "PipelineResult",
    "BaseAnimationNode",
    "ClassifyNode",
    "PlanLectureNode",
    "PlanTeachingScriptNode",
    "CodeAgentNode",
    "CodeAgent",
    "AnimationGraphBuilder",
    "animation_graph",
    "AnimationPipelineRunner",
    "PipelineArtifactManager",
    "run_pipeline",
    "run_coder_step",
    "subject_str",
    "AnimationPipelineAgent",
    "animation_agent",
]

if __name__ == "__main__":
    prompt = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "I want to learn about Hairy Ball theorem."
    )
    result = asyncio.run(run_pipeline(prompt))
    print(result)
