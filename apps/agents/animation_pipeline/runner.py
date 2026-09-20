"""Orchestrator runner for the animation generation pipeline."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from typing import Any

from pydantic_graph import EndMarker, Graph

from animation_pipeline.builder import AnimationGraphBuilder
from animation_pipeline.state import AnimationState
from animation_pipeline.storage import PipelineArtifactManager
from cinematic_director import is_cinematic_mode
from openai_compatible import format_custom_endpoint_error


class AnimationPipelineRunner:
    """Orchestrates end-to-end animation generation across keyframe and graph workflows."""

    def __init__(
        self,
        graph: Graph[AnimationState, None, str] | None = None,
        artifact_manager: PipelineArtifactManager | None = None,
    ) -> None:
        self.graph = graph or AnimationGraphBuilder().build()
        self.artifact_manager = artifact_manager or PipelineArtifactManager()

    async def run(
        self,
        user_query: str,
        *,
        length: str = "medium",
        cinematic: bool = False,
        prompt_index: int | None = None,
        mode: str = "keyframe",
        output_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        """Execute the pipeline, delegating to keyframe engine or graph iteration."""
        if mode == "keyframe":
            return await self._run_keyframe(
                user_query, length=length, output_dir=output_dir
            )

        return await self._run_graph(
            user_query,
            length=length,
            cinematic=cinematic,
            prompt_index=prompt_index,
            mode=mode,
        )

    async def _run_keyframe(
        self,
        user_query: str,
        *,
        length: str = "medium",
        output_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        """Dispatch fast-path decoupled keyframe generation."""
        from keyframe_engine import run_producer_consumer

        total_slides = 3
        if length in ("5m", "medium", "5"):
            total_slides = 3
        elif length in ("10m", "long", "10"):
            total_slides = 4
        elif length in ("short", "1m", "1"):
            total_slides = 2

        res = await asyncio.to_thread(
            run_producer_consumer,
            user_query,
            output_dir=output_dir,
            total_slides=total_slides,
        )
        if res.get("scene_file") and not res.get("scene_path"):
            res["scene_path"] = res["scene_file"]
        return res

    async def _run_graph(
        self,
        user_query: str,
        *,
        length: str = "medium",
        cinematic: bool = False,
        prompt_index: int | None = None,
        mode: str = "continuous",
    ) -> dict[str, Any]:
        """Iterate through the Pydantic Graph state machine with progress streaming."""
        cinematic_active = is_cinematic_mode(user_query, flag=cinematic)
        state = AnimationState(
            user_query=user_query,
            target_length=length,
            cinematic=cinematic_active,
            prompt_index=prompt_index,
            animation_mode=mode,
        )

        summary = ""
        try:
            async with self.graph.iter(state=state) as run:
                async for step in run:
                    if isinstance(step, EndMarker):
                        summary = step.value if isinstance(step.value, str) else ""
                        break
                    for task in step:
                        self._emit_progress(task.node_id)
        except Exception as exc:
            raise RuntimeError(format_custom_endpoint_error(exc)) from exc

        if state.coder_result is not None:
            result = state.coder_result.model_dump(mode="json")
            if prompt_index is not None:
                result["prompt_index"] = prompt_index
            self.artifact_manager.upload_artifacts(state.coder_result, result)
            return result

        return {
            "result": summary,
            "stopped_reason": "classification_failed_or_unsupported",
            "error": summary or "classification_failed_or_unsupported",
            "message": summary or "Domain not supported or classification failed.",
        }

    def _emit_progress(self, node_id: str) -> None:
        """Stream node progress to stderr for Celery and UI consumption."""
        print(f"-> {node_id}", file=sys.stderr, flush=True)
