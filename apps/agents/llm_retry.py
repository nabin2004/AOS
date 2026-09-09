"""Robust retry wrapper with exponential backoff and jitter for transient LLM cold starts and network glitches."""

from __future__ import annotations

import asyncio
import logging
import random
import sys
from typing import Any, Awaitable, Callable, TypeVar

from error_classifier import ErrorCategory, classify_error
from reliability_config import LLM_BACKOFF_BASE, LLM_BACKOFF_MAX, LLM_MAX_RETRIES

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def execute_with_llm_retry(
    async_func: Callable[[], Awaitable[T]],
    *,
    operation_name: str = "LLM Call",
    max_retries: int = LLM_MAX_RETRIES,
    on_progress: Callable[[str, str], None] | None = None,
) -> T:
    """Execute an LLM async operation with automatic retry on 503 cold-start and network errors.

    Emits structured ``-> LLM_COLD_START`` and ``-> LLM_RETRYING`` progress lines
    to notify CLI, Celery, and WebSocket consumers.
    """
    attempt = 0
    while True:
        try:
            return await async_func()
        except Exception as exc:
            attempt += 1
            classified = classify_error(exc)

            if not classified.is_retryable or attempt > max_retries:
                logger.error(
                    "%s failed (attempt %d/%d, not retryable or budget exhausted): %s",
                    operation_name,
                    attempt,
                    max_retries,
                    classified.raw_error,
                )
                raise

            # Determine stage based on error classification
            if classified.category == ErrorCategory.TRANSIENT_LLM_ERROR:
                stage = "LLM_COLD_START"
                user_msg = (
                    f"Starting the AI model… The model was temporarily asleep and is waking up. "
                    f"Retrying automatically (attempt {attempt} of {max_retries})…"
                )
            elif classified.category == ErrorCategory.RATE_LIMIT:
                stage = "RATE_LIMIT_WAIT"
                user_msg = (
                    f"AI service is at capacity. Waiting before retrying (attempt {attempt} of {max_retries})…"
                )
            else:
                stage = "LLM_RETRYING"
                user_msg = (
                    f"Reconnecting to AI service… Retrying automatically (attempt {attempt} of {max_retries})…"
                )

            # Emit structured progress to stderr for parent CLI/process monitors
            progress_line = f"-> {stage} {user_msg}"
            print(progress_line, file=sys.stderr, flush=True)

            if on_progress:
                try:
                    on_progress(stage, user_msg)
                except Exception as cb_exc:
                    logger.warning("on_progress callback error: %s", cb_exc)

            # Exponential backoff with full jitter
            base_delay = min(LLM_BACKOFF_BASE * (1.8 ** (attempt - 1)), LLM_BACKOFF_MAX)
            jitter = random.uniform(0.2, 1.2)
            sleep_duration = base_delay + jitter

            logger.info(
                "%s: %s (%s). Sleeping %.1fs before attempt %d/%d...",
                operation_name,
                classified.category.value,
                stage,
                sleep_duration,
                attempt + 1,
                max_retries,
            )
            await asyncio.sleep(sleep_duration)
