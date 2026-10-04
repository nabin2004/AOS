"""FastAPI routes for MotionGram animation synthesis, validation, and rendering."""

from __future__ import annotations

import logging
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from app.api.deps import CurrentUser, DBSession
from app.schemas.video_generation import VideoRenderCustomResponse
from app.services.motiongram_service import motiongram_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/motiongram", tags=["motiongram"])


# ==========================================
# Request Models
# ==========================================

class MotionGramGenerateRequest(BaseModel):
    prompt: str = Field(..., description="Educational topic or scene description")
    voice_backend: Literal["edge-tts", "pocket-tts", "dsm", "kitten"] = Field(
        default="edge-tts",
        description="Speech model backend for kinetic voice narration",
    )
    voice_name: str = Field(default="alba", description="Voice identifier")
    model_name: str | None = Field(default=None, description="Optional LLM model override")
    base_url: str | None = Field(default=None, description="Optional LLM endpoint override")
    api_key: str | None = Field(default=None, description="Optional LLM API key override")
    max_attempts: int = Field(default=3, ge=1, le=5, description="Max self-healing repair iterations")


class MotionGramValidateRequest(BaseModel):
    yaml_text: str = Field(..., description="MotionGram YAML/JSON specification text")


class MotionGramCompileRequest(BaseModel):
    yaml_text: str = Field(..., description="MotionGram YAML/JSON specification text")


class MotionGramRenderRequest(BaseModel):
    yaml_text: str = Field(..., description="MotionGram YAML/JSON specification text")
    quality: Literal["l", "m", "h", "k"] = Field(default="m", description="Render quality")
    conversation_id: UUID | None = Field(default=None, description="Linked conversation ID")
    prompt: str | None = Field(default=None, description="Original user prompt or title")

    @field_validator("quality", mode="before")
    @classmethod
    def normalize_quality(cls, v: Any) -> str:
        if isinstance(v, str):
            v_clean = v.strip().lower()
            if v_clean.startswith("q") and len(v_clean) == 2 and v_clean[1] in ("l", "m", "h", "k"):
                return v_clean[1]
            if v_clean in ("l", "m", "h", "k"):
                return v_clean
        return v


class MotionGramOneShotRequest(BaseModel):
    prompt: str = Field(..., description="Educational topic to storyboard, compile, and render")
    voice_backend: Literal["edge-tts", "pocket-tts", "dsm", "kitten"] = Field(default="edge-tts")
    voice_name: str = Field(default="alba")
    quality: Literal["l", "m", "h", "k"] = Field(default="m")
    conversation_id: UUID | None = Field(default=None)
    model_name: str | None = Field(default=None)
    base_url: str | None = Field(default=None)
    api_key: str | None = Field(default=None)

    @field_validator("quality", mode="before")
    @classmethod
    def normalize_quality(cls, v: Any) -> str:
        if isinstance(v, str):
            v_clean = v.strip().lower()
            if v_clean.startswith("q") and len(v_clean) == 2 and v_clean[1] in ("l", "m", "h", "k"):
                return v_clean[1]
            if v_clean in ("l", "m", "h", "k"):
                return v_clean
        return v


# ==========================================
# Endpoints
# ==========================================

@router.get("/schema", response_model=None)
async def get_motiongram_schema() -> dict[str, Any]:
    """Return JSON Schema, system prompt, and few-shot examples for MotionGram."""
    return motiongram_service.get_dsl_schema()


@router.post("/validate", response_model=None)
async def validate_motiongram_spec(payload: MotionGramValidateRequest) -> dict[str, Any]:
    """Validate a YAML specification without executing a render."""
    is_valid, msg = motiongram_service.validate_spec(payload.yaml_text)
    return {
        "valid": is_valid,
        "message": "Specification is valid" if is_valid else "Validation failed",
        "repair_prompt": None if is_valid else msg,
    }


@router.post("/compile", response_model=None)
async def compile_motiongram_spec(payload: MotionGramCompileRequest) -> dict[str, Any]:
    """Compile MotionGram YAML specification into a ManimCE Python script."""
    py_code = motiongram_service.compile_spec(payload.yaml_text)
    return {
        "status": "success",
        "code": py_code,
    }


@router.post("/generate", response_model=None)
async def generate_motiongram_spec(
    payload: MotionGramGenerateRequest,
    user: CurrentUser,
) -> dict[str, Any]:
    """Generate a MotionGram specification with self-healing ReAct repair loop."""
    result = await motiongram_service.generate_with_healing(
        prompt=payload.prompt,
        voice_backend=payload.voice_backend,
        voice_name=payload.voice_name,
        model_name=payload.model_name,
        base_url=payload.base_url,
        api_key=payload.api_key,
        max_attempts=payload.max_attempts,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": result.error or "Generation failed",
                "diagnostics": result.diagnostics or [],
                "partial_spec": result.spec_yaml,
            },
        )

    return {
        "status": "success",
        "spec_yaml": result.spec_yaml,
        "compiled_code": result.compiled_code,
        "repair_attempts": result.repair_attempts,
        "diagnostics": result.diagnostics or [],
    }


@router.post("/render", response_model=VideoRenderCustomResponse)
async def render_motiongram_spec(
    payload: MotionGramRenderRequest,
    user: CurrentUser,
    db: DBSession,
) -> Any:
    """Compile and render a MotionGram YAML specification into an MP4 video."""
    return await motiongram_service.render_motiongram(
        yaml_text=payload.yaml_text,
        user_id=user.id,
        db=db,
        conversation_id=payload.conversation_id,
        quality=payload.quality,
        prompt=payload.prompt,
    )


@router.post("/generate-and-render", response_model=VideoRenderCustomResponse)
async def generate_and_render_oneshot(
    payload: MotionGramOneShotRequest,
    user: CurrentUser,
    db: DBSession,
) -> Any:
    """End-to-end: storyboard with self-healing reflection, compile, and render MP4."""
    # 1. Generate valid specification
    gen_result = await motiongram_service.generate_with_healing(
        prompt=payload.prompt,
        voice_backend=payload.voice_backend,
        voice_name=payload.voice_name,
        model_name=payload.model_name,
        base_url=payload.base_url,
        api_key=payload.api_key,
    )

    if not gen_result.success or not gen_result.spec_yaml:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": gen_result.error or "MotionGram generation failed",
                "diagnostics": gen_result.diagnostics or [],
            },
        )

    # 2. Render MP4
    return await motiongram_service.render_motiongram(
        yaml_text=gen_result.spec_yaml,
        user_id=user.id,
        db=db,
        conversation_id=payload.conversation_id,
        quality=payload.quality,
        prompt=payload.prompt,
    )
