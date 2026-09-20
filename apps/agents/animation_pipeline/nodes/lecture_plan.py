"""Lecture planning node integrating manim-composer and manimce-best-practices skills."""

from __future__ import annotations

from dataclasses import dataclass
import sys
from pydantic_graph import BaseNode, End, GraphRunContext

from animation_pipeline.nodes.base import BaseAnimationNode
from animation_pipeline.nodes.teaching_script import PlanTeachingScriptNode
from animation_pipeline.state import AnimationState
from coder_step import subject_str
from ir.manim_ir import Subject
from lecture_planner import lecture_planner_agent


@dataclass
class PlanLectureNode(BaseNode[AnimationState, None, str], BaseAnimationNode):
    """Produces the high-level pedagogical outline using manim-composer and manimce-best-practices."""

    async def run(
        self, ctx: GraphRunContext[AnimationState]
    ) -> PlanTeachingScriptNode | End[str]:
        plan_error: str | None = None
        classification = ctx.state.classification
        topic = classification.topic if classification else "Math Topic"
        subject = classification.subject if classification else Subject.MATH

        try:
            async def _call_planner():
                planner_prompt = (
                    f"Topic: {topic}\n"
                    f"Subject: {subject_str(subject)}\n"
                    f"Target Length: {ctx.state.target_length}\n"
                    f"Cinematic: {ctx.state.cinematic}\n\n"
                    "Consult `manim-composer` to craft a clear pedagogical narrative arc, hook, pacing, and aha moment. "
                    "Consult `manimce-best-practices` to ensure equations, diagrams, and layouts adhere to Manim CE frame-safe standards."
                )
                return await lecture_planner_agent.run(planner_prompt)

            result = await self.execute_agent_call(
                _call_planner, operation_name="Lecture Planner Agent"
            )
            ctx.state.plan = result.output
        except Exception as exc:
            plan_error = self.format_error(exc)
            print(f"planner error: {plan_error}", file=sys.stderr, flush=True)
            ctx.state.plan = None

        if ctx.state.plan is None:
            detail = "Lecture planning failed."
            if plan_error:
                detail = f"{detail} ({plan_error[:400]})"
            return End(detail)

        from animation_pipeline.nodes.teaching_script import PlanTeachingScriptNode

        return PlanTeachingScriptNode()
