"""Teaching script node generating narrative beats aligned with visual actions."""

from __future__ import annotations

from dataclasses import dataclass
import sys
from pydantic_graph import BaseNode, GraphRunContext

from animation_pipeline.nodes.base import BaseAnimationNode
from animation_pipeline.nodes.code_agent import CodeAgentNode
from animation_pipeline.state import AnimationState
from teaching_script import (
    teaching_script_agent,
    teaching_script_user_prompt,
)


@dataclass
class PlanTeachingScriptNode(BaseNode[AnimationState, None, str], BaseAnimationNode):
    """Generates sequential narration beats aligned with visual actions."""

    async def run(
        self, ctx: GraphRunContext[AnimationState]
    ) -> CodeAgentNode:
        classification = ctx.state.classification
        plan = ctx.state.plan
        if classification is None or plan is None:
            return CodeAgentNode()

        try:
            async def _call_teaching_script():
                return await teaching_script_agent.run(
                    teaching_script_user_prompt(
                        classification.topic,
                        self.subject_str(classification.subject),
                        plan,
                        length=ctx.state.target_length,
                        cinematic=ctx.state.cinematic,
                    )
                )

            result = await self.execute_agent_call(
                _call_teaching_script, operation_name="Teaching Script Agent"
            )
            ctx.state.teaching_script = result.output
        except Exception as exc:
            print(
                f"teaching script error: {self.format_error(exc)}",
                file=sys.stderr,
                flush=True,
            )
            ctx.state.teaching_script = None

        return CodeAgentNode()
