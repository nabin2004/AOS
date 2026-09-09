"""Centralized reliability and fault-tolerance configuration for the AOS generation pipeline.

All parameters can be tuned via environment variables.
"""

from __future__ import annotations

import os


def _get_int(key: str, default: int) -> int:
    val = os.getenv(key, "").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _get_float(key: str, default: float) -> float:
    val = os.getenv(key, "").strip()
    if not val:
        return default
    try:
        return float(val)
    except ValueError:
        return default


# --- LLM Fault Tolerance & Cold Start ---
LLM_MAX_RETRIES: int = _get_int("AOS_LLM_MAX_RETRIES", 6)
LLM_BACKOFF_BASE: float = _get_float("AOS_LLM_BACKOFF_BASE", 2.0)
LLM_BACKOFF_MAX: float = _get_float("AOS_LLM_BACKOFF_MAX", 30.0)
LLM_CONNECT_TIMEOUT: float = _get_float("AOS_LLM_CONNECT_TIMEOUT", 30.0)
LLM_READ_TIMEOUT: float = _get_float("AOS_LLM_READ_TIMEOUT", 180.0)
LLM_WARMUP_MAX_WAIT_S: float = _get_float("AOS_LLM_WARMUP_MAX_WAIT_S", 150.0)

# --- Manim Code Repair & Render Limits ---
CODE_REPAIR_MAX_ATTEMPTS: int = _get_int("AOS_CODE_REPAIR_MAX_ATTEMPTS", 3)
RENDER_TIMEOUT_SECONDS: int = _get_int("AOS_RENDER_TIMEOUT_SECONDS", 180)
MIN_VIDEO_SIZE_BYTES: int = _get_int("AOS_MIN_VIDEO_SIZE_BYTES", 1024)

# --- Watchdog & Job Timeout ---
JOB_TIMEOUT_SECONDS: int = _get_int("AOS_JOB_TIMEOUT_SECONDS", 1200)
WATCHDOG_STALE_SECONDS: int = _get_int("AOS_WATCHDOG_STALE_SECONDS", 300)
POLL_INTERVAL_SECONDS: float = _get_float("AOS_POLL_INTERVAL_SECONDS", 2.0)
