"""Modular, Object-Oriented Animation Pipeline Package for AOS."""

from animation_pipeline.agent import (
    AnimationPipelineAgent,
    PipelineResult,
    animation_agent,
)
from animation_pipeline.builder import AnimationGraphBuilder
from animation_pipeline.nodes import (
    BaseAnimationNode,
    ClassifyNode,
    CodeAgent,
    CodeAgentNode,
    PlanLectureNode,
    PlanTeachingScriptNode,
)
from animation_pipeline.runner import AnimationPipelineRunner
from animation_pipeline.state import AnimationState
from animation_pipeline.storage import PipelineArtifactManager
from coder_step import run_coder_step, subject_str

# Resident instances for immediate usage
_default_builder = AnimationGraphBuilder()
animation_graph = _default_builder.build()

_default_runner = AnimationPipelineRunner(graph=animation_graph)
run_pipeline = _default_runner.run

__all__ = [
    # State & Models
    "AnimationState",
    "PipelineResult",
    # Nodes
    "BaseAnimationNode",
    "ClassifyNode",
    "PlanLectureNode",
    "PlanTeachingScriptNode",
    "CodeAgentNode",
    "CodeAgent",
    # Builders & Graphs
    "AnimationGraphBuilder",
    "animation_graph",
    # Runners & Storage
    "AnimationPipelineRunner",
    "PipelineArtifactManager",
    "run_pipeline",
    "run_coder_step",
    "subject_str",
    # Agent
    "AnimationPipelineAgent",
    "animation_agent",
]
