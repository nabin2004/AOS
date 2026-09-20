"""Graph node classes for the animation pipeline."""

from animation_pipeline.nodes.base import BaseAnimationNode
from animation_pipeline.nodes.classify import ClassifyNode
from animation_pipeline.nodes.code_agent import CodeAgent, CodeAgentNode
from animation_pipeline.nodes.lecture_plan import PlanLectureNode
from animation_pipeline.nodes.teaching_script import PlanTeachingScriptNode

__all__ = [
    "BaseAnimationNode",
    "ClassifyNode",
    "PlanLectureNode",
    "PlanTeachingScriptNode",
    "CodeAgentNode",
    "CodeAgent",
]
