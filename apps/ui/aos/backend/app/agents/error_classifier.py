"""Backend error classification and user-friendly message mapping."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


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


_RE_503 = re.compile(r"\b(503|502|504|service unavailable|bad gateway|gateway timeout)\b", re.I)
_RE_COLD_START = re.compile(r"(cold start|scaling up|waking up|serverless container|booting)", re.I)
_RE_RATE_LIMIT = re.compile(r"\b(429|rate limit|quota exceeded|too many requests)\b", re.I)
_RE_AUTH = re.compile(r"\b(401|403|unauthorized|forbidden|invalid[ _]?api[ _]?key|expired token|authentication failed)\b", re.I)
_RE_NETWORK = re.compile(r"(connecterror|connection refused|connect timeout|econnrefused|econnreset|connection reset)", re.I)
_RE_TIMEOUT = re.compile(r"(render timeout|timeoutexpired|process timed out|timed out after)", re.I)
_RE_VIDEO_VAL = re.compile(r"(video_validation_failed|0[ -]?byte|no video stream|duration is 0|corrupted video|no mp4 found)", re.I)
_RE_SYNTAX = re.compile(r"(syntaxerror|indentationerror|parse error|invalid syntax|no_scene_class_found)", re.I)
_RE_MANIM = re.compile(r"(manim|latex error|standalone\.cls|mobject|compile_failed)", re.I)


def classify_error(error: Exception | str | None) -> ClassifiedError:
    if error is None:
        return ClassifiedError(
            category=ErrorCategory.INTERNAL_ERROR,
            is_retryable=False,
            is_repairable=False,
            user_message="An unexpected issue occurred.",
            developer_details="None",
            raw_error="",
        )

    raw_error = f"{type(error).__name__}: {error}" if isinstance(error, BaseException) else str(error).strip()
    lowered = raw_error.lower()

    if _RE_AUTH.search(lowered):
        return ClassifiedError(
            category=ErrorCategory.AUTHENTICATION_ERROR,
            is_retryable=False,
            is_repairable=False,
            user_message="AI service authentication failed. Please check your API key in Settings.",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    if _RE_503.search(lowered) or _RE_COLD_START.search(lowered):
        return ClassifiedError(
            category=ErrorCategory.TRANSIENT_LLM_ERROR,
            is_retryable=True,
            is_repairable=False,
            user_message="The AI model took too long to boot from its scaled-down state. Your prompt has been preserved — click Retry to try again.",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    if _RE_RATE_LIMIT.search(lowered):
        return ClassifiedError(
            category=ErrorCategory.RATE_LIMIT,
            is_retryable=True,
            is_repairable=False,
            user_message="The AI service rate limit was reached. Please wait a moment before trying again.",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    if _RE_NETWORK.search(lowered):
        return ClassifiedError(
            category=ErrorCategory.NETWORK_ERROR,
            is_retryable=True,
            is_repairable=False,
            user_message="Network connection to the AI service was interrupted. Please check your internet connection.",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    if _RE_TIMEOUT.search(lowered):
        return ClassifiedError(
            category=ErrorCategory.RENDER_TIMEOUT,
            is_retryable=False,
            is_repairable=True,
            user_message="Animation rendering timed out after automated attempts. Try a simpler prompt or shorter scene.",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    if _RE_VIDEO_VAL.search(lowered):
        return ClassifiedError(
            category=ErrorCategory.VIDEO_VALIDATION_ERROR,
            is_retryable=False,
            is_repairable=True,
            user_message="The generated video file was incomplete or unplayable after automated repair attempts.",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    if _RE_SYNTAX.search(lowered) or _RE_MANIM.search(lowered):
        return ClassifiedError(
            category=ErrorCategory.MANIM_RENDER_ERROR,
            is_retryable=False,
            is_repairable=True,
            user_message="The generated animation code encountered rendering errors that could not be automatically resolved.",
            developer_details=raw_error,
            raw_error=raw_error,
        )

    return ClassifiedError(
        category=ErrorCategory.INTERNAL_ERROR,
        is_retryable=False,
        is_repairable=False,
        user_message="We couldn't generate the animation after several automatic recovery attempts. Your prompt was saved.",
        developer_details=raw_error,
        raw_error=raw_error,
    )
