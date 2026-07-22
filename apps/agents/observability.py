"""Logfire and batch-mode toggles for AOS agents."""

from __future__ import annotations

import os

import logfire

_FALSE = frozenset({"0", "false", "no", "off"})


def _env_flag(name: str, *, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() not in _FALSE


def logfire_enabled() -> bool:
    return _env_flag("AOS_LOGFIRE", default="1")


def sft_batch_enabled() -> bool:
    return _env_flag("AOS_SFT_BATCH", default="0")


def configure_logfire() -> None:
    if logfire_enabled():
        logfire.configure(send_to_logfire="if-token-present")
        logfire.instrument_pydantic_ai()
