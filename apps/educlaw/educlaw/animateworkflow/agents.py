"""Animate workflow CLI runner and agent orchestrator entrypoint."""

from __future__ import annotations

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from rich.prompt import Prompt

from educlaw.agent.deps import AgentDeps
from educlaw.animateworkflow.contracts import FinalCode, LessonPlan, NarrationPlan, PipelineState, RequestClassification
from educlaw.animateworkflow.loop import (
    MAX_COMPILATION_REPLANS,
    WorkflowOrchestrator,
    build_agents,
    normalize_lesson_plan as _normalize_lesson_plan,
)
from educlaw.settings import Settings

load_dotenv()


async def run_workflow(
    user_request: str,
    *,
    cwd: Path | None = None,
    deps: AgentDeps | None = None,
    settings: Settings | None = None,
) -> PipelineState:
    """Run the educational Manim animation workflow using the robust orchestrator loop."""
    orchestrator = WorkflowOrchestrator(
        deps=deps,
        settings=settings,
        max_replans=MAX_COMPILATION_REPLANS,
    )
    return await orchestrator.run(user_request, workspace_dir=cwd)


async def main() -> None:
    user_request = Prompt.ask("Enter your request for educational video content:")
    settings = Settings.from_env()
    workspace_dir = Path.cwd() / "workspace" / "coder"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    orchestrator = WorkflowOrchestrator(
        settings=settings,
        max_replans=MAX_COMPILATION_REPLANS,
    )

    state = await orchestrator.run(user_request, workspace_dir=workspace_dir)

    print("\n" + "=" * 50)
    if state.compile_result and state.compile_result.success:
        print(f"[SUCCESS] Video rendered at: {state.compile_result.output_path}")
    else:
        print("[FAIL] Video generation could not produce a valid render.")


if __name__ == "__main__":
    asyncio.run(main())