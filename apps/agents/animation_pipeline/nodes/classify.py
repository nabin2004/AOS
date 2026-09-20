"""Classification node for determining lecture subject and topic."""

from __future__ import annotations

from dataclasses import dataclass
import sys
from pydantic_graph import BaseNode, End, GraphRunContext

from animation_pipeline.nodes.base import BaseAnimationNode
from animation_pipeline.nodes.lecture_plan import PlanLectureNode
from animation_pipeline.state import AnimationState
from classifier_agent import classifier_agent
from ir.manim_ir import Subject


@dataclass
class ClassifyNode(BaseNode[AnimationState, None, str], BaseAnimationNode):
    """Classifies user request into domain subject and verified topic."""

    async def run(
        self, ctx: GraphRunContext[AnimationState]
    ) -> PlanLectureNode | End[str]:
        classify_error: str | None = None
        try:
            async def _call_classify():
                return await classifier_agent.run(ctx.state.user_query)

            result = await self.execute_agent_call(
                _call_classify, operation_name="Classifier Agent"
            )
            ctx.state.classification = result.output
        except Exception as exc:
            classify_error = self.format_error(exc)
            print(f"classifier error: {classify_error}", file=sys.stderr, flush=True)
            ctx.state.classification = None

        if (
            ctx.state.classification is None
            or ctx.state.classification.subject == Subject.UNKNOWN
        ):
            detail = "Domain not supported or classification failed."
            if classify_error:
                detail = f"{detail} ({classify_error[:400]})"
            return End(detail)

        from animation_pipeline.nodes.lecture_plan import PlanLectureNode

        return PlanLectureNode()
