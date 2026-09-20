"""Interactive Pydantic AI Agent interface for the Animation Pipeline."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from animation_pipeline.runner import AnimationPipelineRunner
from llm_config import model_for_agent, settings_for


class PipelineResult(BaseModel):
    """Structured result model returned by the animation pipeline agent tool."""

    result: str
    stopped_reason: str
    compile_ok: bool
    scene_name: str | None = None
    run_dir: str | None = None
    audio: int | None = None
    error: str | None = None
    message: str | None = None


class AnimationPipelineAgent:
    """Encapsulates the Pydantic AI interactive frontend agent and its tools."""

    def __init__(
        self,
        runner: AnimationPipelineRunner | None = None,
        model_name: str | None = None,
    ) -> None:
        self.runner = runner or AnimationPipelineRunner()
        self.model_name = model_name or model_for_agent("animation")
        self.agent = Agent(
            self.model_name,
            name="Manim Animation Pipeline",
            description="Runs the full educational animation graph pipeline.",
            model_settings=settings_for("animation"),
            system_prompt=(
                "You are the interactive frontend for the Manim animation pipeline.\n"
                "Call `generate_educational_animation` with the user's exact query to start the generation.\n"
                "Do not write long reasoning or preambles, just call the tool."
            ),
        )
        self._register_tools()

    def _register_tools(self) -> None:
        @self.agent.tool
        async def generate_educational_animation(
            ctx: RunContext, user_query: str
        ) -> PipelineResult:
            """Execute the full animation pipeline (classify, plan, script, code, compile) for the user's query."""
            result = await self.runner.run(user_query)
            return PipelineResult(
                result=result.get("result", result.get("summary", "")),
                stopped_reason=result.get("stopped_reason", "unknown"),
                compile_ok=result.get("compile_ok", False),
                scene_name=result.get("scene_name"),
                run_dir=result.get("run_dir"),
                audio=len(result.get("audio_paths", [])),
                error=result.get("error"),
                message=result.get("message"),
            )


# Default resident instance and exports for pai web
_pipeline_agent_instance = AnimationPipelineAgent()
animation_agent = _pipeline_agent_instance.agent
