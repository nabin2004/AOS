"""MotionGram Service for deterministic, kinetic teaching animations in AOS.

Implements the declarative YAML/JSON DSL, self-healing reflection loop,
Pydantic v2 validation, ManimCE compilation, and kinetic voiceover narration
via AOSSpeechService / Dytto with `<bookmark mark='...'/>` synchronization.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Literal
from uuid import UUID, uuid4

import httpx
import yaml
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# Resolve paths for motiongram package and AOS repo root
_current_file = Path(__file__).resolve()
_potential_roots: list[Path] = [Path("/app")]
for _parent in _current_file.parents:
    if (_parent / "packages" / "motiongram").exists() or (_parent / "pyproject.toml").exists():
        _potential_roots.insert(0, _parent)

_candidate_paths: list[Path] = [
    Path("/app/packages/motiongram/src"),
    Path("/app/packages/motiongram"),
    Path(r"C:\Users\nabin\Desktop\myall\ManimLite\src"),
]
for _r in _potential_roots:
    _candidate_paths.append(_r / "packages" / "motiongram" / "src")
    _candidate_paths.append(_r / "packages" / "motiongram")
    _candidate_paths.append(_r)

for _p in _candidate_paths:
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# MotionGram imports
try:
    from motiongram.manimgram.compiler import compile_dsl
    from motiongram.manimgram.llm import (
        MANIMGRAM_SYSTEM_PROMPT,
        FEW_SHOT_EXAMPLES,
        format_repair_prompt,
        get_json_schema,
        get_system_prompt,
        validate_and_generate_repair,
    )
    from motiongram.manimgram.schema import ManimGramScene
    MOTIONGRAM_AVAILABLE = True
    logging.getLogger(__name__).info("MotionGram package successfully loaded into AOS backend.")
except ImportError as exc:
    logging.getLogger(__name__).warning("MotionGram failed to import: %s", exc)
    MOTIONGRAM_AVAILABLE = False
    compile_dsl = None  # type: ignore[assignment]
    validate_and_generate_repair = None  # type: ignore[assignment]
    format_repair_prompt = None  # type: ignore[assignment]
    get_json_schema = None  # type: ignore[assignment]
    get_system_prompt = None  # type: ignore[assignment]
    MANIMGRAM_SYSTEM_PROMPT = ""
    FEW_SHOT_EXAMPLES = []

from app.agents.hitl_agents import _resolve_llm_config
from app.repositories import video_generation as video_repo
from app.schemas.video_generation import VideoRenderCustomResponse
from app.services.manim_code import repair_manim_code
from app.services.manim_studio import manim_studio_service

logger = logging.getLogger(__name__)


@dataclass
class MotionGramGenerationResult:
    """Outcome of self-healing MotionGram generation."""

    success: bool
    spec_yaml: str
    compiled_code: str | None = None
    repair_attempts: int = 0
    diagnostics: list[str] | None = None
    error: str | None = None


class MotionGramService:
    """Manages MotionGram storyboard generation, validation, compilation, and rendering."""

    def __init__(self) -> None:
        self.max_attempts = 3

    def get_dsl_schema(self) -> dict[str, Any]:
        """Return JSON Schema for structured outputs and UI schema forms."""
        if not MOTIONGRAM_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MotionGram engine is not available on this server.",
            )
        return {
            "system_prompt": get_system_prompt(),
            "schema": get_json_schema(),
            "few_shot_examples": FEW_SHOT_EXAMPLES,
        }

    def validate_spec(self, yaml_text: str) -> tuple[bool, str]:
        """Validate a YAML/JSON DSL specification against ManimGramScene schema.
        
        Returns:
            (is_valid, message_or_repair_prompt)
        """
        if not MOTIONGRAM_AVAILABLE:
            return False, "MotionGram package is not available."

        return validate_and_generate_repair(yaml_text)

    def compile_spec(self, yaml_text: str) -> str:
        """Compile a MotionGram YAML specification into a ManimCE Python script."""
        if not MOTIONGRAM_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MotionGram compiler is not available on this server.",
            )

        is_valid, err_msg = self.validate_spec(yaml_text)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "Schema validation failed", "repair_prompt": err_msg},
            )

        try:
            return compile_dsl(yaml_text)
        except Exception as exc:
            logger.exception("MotionGram compilation error")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "DSL Compilation failed", "diagnostic": str(exc)},
            ) from exc

    async def _call_llm(
        self,
        messages: list[dict[str, str]],
        *,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        """Call LLM via OpenAI-compatible endpoint with resolved credentials."""
        key, url, model = _resolve_llm_config(
            api_key=api_key, base_url=base_url, model_name=model_name
        )

        headers = {
            "Content-Type": "application/json",
        }
        if key and key != "EMPTY":
            headers["Authorization"] = f"Bearer {key}"
        if "openrouter.ai" in url:
            headers["HTTP-Referer"] = "https://github.com/nabin2004/AOS"
            headers["X-Title"] = "AOS MotionGram Visual Studio"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"LLM API error ({resp.status_code}): {resp.text[:300]}"
                )
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise RuntimeError("LLM returned no completion choices.")
            content = choices[0].get("message", {}).get("content", "")
            return content.strip()

    def _clean_yaml_response(self, text: str) -> str:
        """Strip markdown fences (```yaml ... ```) if LLM emitted them."""
        text = text.strip()
        m = re.search(r"```(?:yaml|json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return text

    async def generate_with_healing(
        self,
        prompt: str,
        *,
        voice_backend: Literal["edge-tts", "pocket-tts", "dsm", "kitten"] = "edge-tts",
        voice_name: str = "alba",
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        max_attempts: int = 3,
    ) -> MotionGramGenerationResult:
        """Generate a valid MotionGram animation specification with self-healing ReAct loop."""
        if not MOTIONGRAM_AVAILABLE:
            return MotionGramGenerationResult(
                success=False,
                spec_yaml="",
                error="MotionGram package not available on backend.",
            )

        system_prompt = MANIMGRAM_SYSTEM_PROMPT + f"""

VOICEOVER BACKEND PREFERENCE:
- Preferred Speech Backend: {voice_backend}
- Preferred Voice: {voice_name}
- Ensure 'scene.type: VoiceoverScene' is set.
- Ensure audio cache_dir is 'voiceover_cache'.
"""

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        # Add few-shot examples
        for ex in FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": ex["prompt"]})
            messages.append({"role": "assistant", "content": ex["yaml"]})

        user_content = (
            f"Create a high-impact, short educational animation with synchronized voice narration for:\n"
            f"Topic: {prompt}\n\n"
            f"Return ONLY valid MotionGram YAML. Embed <bookmark mark='...'/> tags for kinetic reveals."
        )
        messages.append({"role": "user", "content": user_content})

        diagnostics: list[str] = []
        current_spec = ""

        for attempt in range(1, max_attempts + 1):
            logger.info("MotionGram storyboard generation attempt %d/%d", attempt, max_attempts)
            try:
                raw_response = await self._call_llm(
                    messages,
                    model_name=model_name,
                    base_url=base_url,
                    api_key=api_key,
                )
                current_spec = self._clean_yaml_response(raw_response)
            except Exception as exc:
                err_msg = f"Attempt {attempt}: LLM call failed: {exc}"
                logger.warning(err_msg)
                diagnostics.append(err_msg)
                if attempt == max_attempts:
                    return MotionGramGenerationResult(
                        success=False,
                        spec_yaml=current_spec,
                        repair_attempts=attempt,
                        diagnostics=diagnostics,
                        error=str(exc),
                    )
                continue

            # Stage 1: Pydantic Schema Validation
            is_valid, validation_msg = self.validate_spec(current_spec)
            if not is_valid:
                err_msg = f"Attempt {attempt}: Schema validation failed."
                logger.info(err_msg)
                diagnostics.append(err_msg)
                messages.append({"role": "assistant", "content": current_spec})
                messages.append({"role": "user", "content": validation_msg})
                continue

            # Stage 2: ManimCE Compilation Check
            try:
                compiled_code = compile_dsl(current_spec)
                logger.info("MotionGram specification successfully compiled on attempt %d", attempt)
                return MotionGramGenerationResult(
                    success=True,
                    spec_yaml=current_spec,
                    compiled_code=compiled_code,
                    repair_attempts=attempt,
                    diagnostics=diagnostics,
                )
            except Exception as compile_exc:
                err_msg = f"Attempt {attempt}: Compilation failed: {compile_exc}"
                logger.warning(err_msg)
                diagnostics.append(err_msg)
                repair_prompt = format_repair_prompt(current_spec, str(compile_exc))
                messages.append({"role": "assistant", "content": current_spec})
                messages.append({"role": "user", "content": repair_prompt})

        return MotionGramGenerationResult(
            success=False,
            spec_yaml=current_spec,
            repair_attempts=max_attempts,
            diagnostics=diagnostics,
            error="Exceeded maximum self-healing repair attempts.",
        )

    async def render_motiongram(
        self,
        yaml_text: str,
        user_id: UUID,
        db: AsyncSession,
        conversation_id: UUID | None = None,
        quality: Literal["l", "m", "h", "k"] = "m",
        prompt: str | None = None,
    ) -> VideoRenderCustomResponse:
        """Compile MotionGram YAML specification into ManimCE and render video."""
        # 1. Compile YAML to Python code
        compiled_code = self.compile_spec(yaml_text)

        # 2. Extract scene name from YAML
        scene_name = "GeneratedScene"
        try:
            spec_data = yaml.safe_load(yaml_text)
            if isinstance(spec_data, dict) and "scene" in spec_data:
                scene_name = spec_data["scene"].get("class_name", scene_name)
        except Exception:
            pass

        # 3. Render via ManimStudioService renderer
        return await manim_studio_service.render_custom_code(
            code=compiled_code,
            scene_name=scene_name,
            quality=quality,
            user_id=user_id,
            db=db,
            conversation_id=conversation_id,
            prompt=prompt or f"MotionGram Scene: {scene_name}",
            skip_preflight=False,
        )


# Global singleton
motiongram_service = MotionGramService()
