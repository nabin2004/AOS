from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

AGENTS_ROOT = Path(__file__).resolve().parent.parent.parent
SFT_DIR = AGENTS_ROOT / "sft_data_gen"
sys.path.insert(0, str(AGENTS_ROOT))

from apps.agents.dbos_setup import DBOS_enabled
from observability import logfire_enabled, sft_batch_enabled


def _import_collect_traces():
    import importlib.util

    path = SFT_DIR / "collect_traces.py"
    spec = importlib.util.spec_from_file_location("collect_traces", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_logfire_disabled_by_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AOS_LOGFIRE", "0")
    assert logfire_enabled() is False


def test_sft_batch_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AOS_SFT_BATCH", "1")
    assert sft_batch_enabled() is True


def test_dbos_disabled_when_aos_dbos_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AOS_DBOS", "0")
    monkeypatch.setenv("DBOS_SYSTEM_DATABASE_URL", "postgresql://localhost/dbos")
    assert dbos_enabled() is False


def test_apply_batch_env_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _import_collect_traces()
    monkeypatch.delenv("AOS_LOGFIRE", raising=False)
    monkeypatch.delenv("AOS_DBOS", raising=False)
    monkeypatch.delenv("AOS_SFT_BATCH", raising=False)
    mod.apply_batch_env(fast=True)
    assert os.environ["AOS_LOGFIRE"] == "0"
    assert os.environ["AOS_DBOS"] == "0"
    assert os.environ["AOS_SFT_BATCH"] == "1"


def test_configure_logfire_skipped_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AOS_LOGFIRE", "0")
    with patch("observability.logfire.configure") as configure:
        with patch("observability.logfire.instrument_pydantic_ai") as instrument:
            from observability import configure_logfire

            configure_logfire()
    configure.assert_not_called()
    instrument.assert_not_called()


def test_select_prompts_applies_limit_after_resume(tmp_path: Path) -> None:
    """--limit must take the next N unfinished prompts, not the first N rows."""
    mod = _import_collect_traces()
    records = [{"index": i, "prompt": f"p{i}"} for i in range(10)]
    manifest = tmp_path / "batch.jsonl"
    # Indices 0-4 already completed
    manifest.write_text(
        "\n".join(
            json.dumps({"index": i, "status": "ok", "compile_ok": True})
            for i in range(5)
        )
        + "\n",
        encoding="utf-8",
    )
    selected = mod.select_prompts(
        records,
        offset=0,
        limit=3,
        indices=None,
        resume=True,
        skip_failed=False,
        manifest_path=manifest,
    )
    assert [r["index"] for r in selected] == [5, 6, 7]


def test_collect_traces_runs_concurrent_tasks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    mod = _import_collect_traces()
    prompts = tmp_path / "prompts.jsonl"
    prompts.write_text(
        '{"index": 0, "prompt": "a"}\n{"index": 1, "prompt": "b"}\n',
        encoding="utf-8",
    )
    manifest = tmp_path / "batch.jsonl"
    summary = tmp_path / "summary.json"

    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()

    async def fake_pipeline(prompt: str, *, prompt_index: int | None = None) -> dict:
        nonlocal in_flight, max_in_flight
        async with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.05)
        async with lock:
            in_flight -= 1
        return {
            "index": prompt_index,
            "prompt": prompt,
            "status": "ok",
            "compile_ok": True,
            "run_dir": f"workspace/coder_runs/run-{prompt_index}",
            "traces_path": "traces/messages.json",
            "stopped_reason": "completed",
            "timestamp": "2026-01-01T00:00:00+00:00",
        }

    async def _run() -> dict:
        monkeypatch.setattr(mod, "_run_one_impl", fake_pipeline)
        args = mod.parse_args(
            [
                "--prompts",
                str(prompts),
                "--manifest",
                str(manifest),
                "--summary",
                str(summary),
                "--concurrency",
                "2",
                "--no-resume",
            ]
        )
        args.warmup = False
        return await mod.collect_traces(args)

    stats = asyncio.run(_run())

    assert stats["attempted"] == 2
    assert stats["ok"] == 2
    assert max_in_flight == 2
