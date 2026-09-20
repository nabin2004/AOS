"""Code agent node coordinating Manim code generation and compilation."""

from __future__ import annotations

from dataclasses import dataclass
from pydantic_graph import BaseNode, End, GraphRunContext

from animation_pipeline.nodes.base import BaseAnimationNode
from animation_pipeline.state import AnimationState
from coder_step import run_coder_step


@dataclass
class CodeAgentNode(BaseNode[AnimationState, None, str], BaseAnimationNode):
    """Synthesizes, compiles, and verifies the final Manim scene code."""

    async def run(self, ctx: GraphRunContext[AnimationState]) -> End[str]:
        assert ctx.state.classification is not None, "Classification required for code agent"
        coder_result = await run_coder_step(
            ctx.state.classification.topic,
            ctx.state.classification.subject,
            ctx.state.plan,
            teaching_script=ctx.state.teaching_script,
            user_prompt=ctx.state.user_query,
            prompt_index=ctx.state.prompt_index,
            length=ctx.state.target_length,
            cinematic=ctx.state.cinematic,
            animation_mode=ctx.state.animation_mode,
        )
        ctx.state.run_dir = coder_result.run_dir
        ctx.state.coder_result = coder_result
        ctx.state.code = coder_result.code

        end_summary = (
            f"stopped={coder_result.stopped_reason} "
            f"compile_ok={coder_result.compile_ok} "
            f"scene={coder_result.scene_name} "
            f"run_dir={coder_result.run_dir} "
            f"audio={len(coder_result.audio_paths)}"
        )
        return End(end_summary)


# Backward-compatibility alias
CodeAgent = CodeAgentNode
