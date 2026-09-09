"""Centralized error classification and friendly user messaging for AOS generation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any


class ErrorCategory(str, Enum):
    TRANSIENT_LLM_ERROR = "TRANSIENT_LLM_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    LLM_INVALID_RESPONSE = "LLM_INVALID_RESPONSE"
    CODE_GENERATION_ERROR = "CODE_GENERATION_ERROR"
    CODE_VALIDATION_ERROR = "CODE_VALIDATION_ERROR"
    MANIM_RENDER_ERROR = "MANIM_RENDER_ERROR"
    RENDER_TIMEOUT = "RENDER_TIMEOUT"
    VIDEO_VALIDATION_ERROR = "VIDEO_VALIDATION_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class ClassifiedError:
    category: ErrorCategory
    is_retryable: bool
    is_repairable: bool
    user_message: str
    developer_details: str
    raw_error: str


# Regex patterns for error matching
_RE_503 = re.compile(r"\b(503|502|504|service unavailable|bad gateway|gateway timeout)\b", re.I)
_RE_COLD_START = re.compile(r"(cold start|scaling up|waking up|serverless container|booting)", re.I)
_RE_RATE_LIMIT = re.compile(r"\b(429|rate limit|quota exceeded|too many requests|tokens per minute)\b", re.I)
_RE_AUTH = re.compile(r"\b(401|403|unauthorized|forbidden|invalid[ _]?api[ _]?key|expired token|authentication failed)\b", re.I)
_RE_NETWORK = re.compile(r"(connecterror|connection refused|connect timeout|econnrefused|econnreset|connection reset|dns lookup|nodename nor servname)", re.I)
_RE_SYNTAX = re.compile(r"(syntaxerror|indentationerror|parse error|invalid syntax)", re.I)
_RE_MANIM = re.compile(r"(manim|latex error|standalone\.cls|mobject|scene|cannot find font|tex expression|error while rendering)", re.I)
_RE_TIMEOUT = re.compile(r"(render timeout|timeoutexpired|process timed out|timed out after)", re.I)
_RE_VIDEO_VAL = re.compile(r"(0[ -]?byte|no video stream|duration is 0|corrupted video|no mp4 found|empty output file|video_validation_failed)", re.I)


def classify_error(error: Exception | str | None) -> ClassifiedError:
    """Analyze an exception or error string and return a structured ClassifiedError."""
    if error is None:
        return ClassifiedError(
            category=ErrorCategory.INTERNAL_ERROR,
            is_retryable=False,
            is_repairable=False,
            user_message="An unexpected issue occurred.",
            developer_details="Error object was None",
            raw_error="",
        )

    if isinstance(error, BaseException):
        raw_error = f"{type(error).__name__}: {error}"
    else:
        raw_error = str(error).strip()

    lowered = raw_error.lower()

    # 1. Authentication errors (Non-retryable)
    if _RE_AUTH.search(lowered):
        return ClassifiedError(
            category=ErrorCategory.AUTHENTICATION_ERROR,
            is_retryable=False,
            is_repairable=False,
            user_message="AI service authentication failed. Please check your API credentials.",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    # 2. Rate limits (Retryable with backoff)
    if _RE_RATE_LIMIT.search(lowered):
        return ClassifiedError(
            category=ErrorCategory.RATE_LIMIT,
            is_retryable=True,
            is_repairable=False,
            user_message="The AI service is currently busy. We're waiting a moment before retrying.",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    # 3. Transient LLM cold-start / 503 / 502 / 504
    if _RE_503.search(lowered) or _RE_COLD_START.search(lowered):
        return ClassifiedError(
            category=ErrorCategory.TRANSIENT_LLM_ERROR,
            is_retryable=True,
            is_repairable=False,
            user_message="Starting the AI model… The service is waking up from idle and will start automatically.",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    # 4. Network / Connection errors (Retryable)
    if _RE_NETWORK.search(lowered):
        return ClassifiedError(
            category=ErrorCategory.NETWORK_ERROR,
            is_retryable=True,
            is_repairable=False,
            user_message="Network connection to the AI service was momentarily interrupted. Reconnecting…",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    # 5. Render timeouts
    if _RE_TIMEOUT.search(lowered):
        return ClassifiedError(
            category=ErrorCategory.RENDER_TIMEOUT,
            is_retryable=False,
            is_repairable=True,
            user_message="Animation rendering took too long. Optimizing scene complexity to render faster…",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    # 6. Video Validation Errors
    if _RE_VIDEO_VAL.search(lowered) or "no_mp4_found" in lowered:
        return ClassifiedError(
            category=ErrorCategory.VIDEO_VALIDATION_ERROR,
            is_retryable=False,
            is_repairable=True,
            user_message="The rendered video was incomplete or unreadable. Regenerating scene…",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    # 7. Code syntax / AST validation errors (Repairable)
    if _RE_SYNTAX.search(lowered) or "syntax_error" in lowered or "missing_voiceover_scene" in lowered:
        return ClassifiedError(
            category=ErrorCategory.CODE_VALIDATION_ERROR,
            is_retryable=False,
            is_repairable=True,
            user_message="The generated animation code needed adjustments. Fixing code syntax automatically…",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    # 8. Manim runtime render errors (Repairable)
    if _RE_MANIM.search(lowered) or "compile_failed" in lowered or "latex" in lowered:
        return ClassifiedError(
            category=ErrorCategory.MANIM_RENDER_ERROR,
            is_retryable=False,
            is_repairable=True,
            user_message="Encountered an animation rendering issue. Fixing scene elements automatically…",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    # 9. LLM invalid / empty response
    if "empty response" in lowered or "no json" in lowered or "invalid response" in lowered:
        return ClassifiedError(
            category=ErrorCategory.LLM_INVALID_RESPONSE,
            is_retryable=True,
            is_repairable=False,
            user_message="AI returned an incomplete response. Retrying generation…",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    # 10. Fallback internal error
    return ClassifiedError(
        category=ErrorCategory.INTERNAL_ERROR,
        is_retryable=False,
        is_repairable=True,
        user_message="Encountered an unexpected pipeline issue. Attempting automated recovery…",
        developer_details=raw_error,
        raw_error=raw_error,
    )
