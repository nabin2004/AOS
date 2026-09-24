"""Unit tests for the HITL local dev runner and local logging system."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from rich.console import Console

from app.core.local_logging import (
    HitlRunStore,
    HitlTerminalObserver,
    disable_logfire_remote,
    serialize_model_messages,
)
from app.schemas.video_generation import VideoClassifyResponse
from app.services.manim_code import CodeRepair, PreflightResult
from dev_hitl import (
    run_classify_stage,
    run_code_stage,
    run_compose_stage,
    run_repair_stage,
)


def test_disable_logfire_remote():
    """Verify that disable_logfire_remote does not crash and disables network export."""
    disable_logfire_remote()


def test_hitl_run_store(tmp_path: Path):
    """Verify local run store writes structured JSON files and updates last_run.json."""
    store = HitlRunStore(log_dir=tmp_path)
    preflight = PreflightResult(valid=True, status="safe", blocking=False)
    repair = CodeRepair(code="from manim import *", changes=("rewrote index",))

    log_path = store.record_run(
        stage="code",
        topic="Fourier Transform",
        model_name="mock:TestModel",
        duration=0.45,
        success=True,
        preflight=preflight,
        repair=repair,
        artifacts={"code": "class S(Scene): pass"},
    )

    assert log_path.exists()
    assert store.last_run_file.exists()

    data = json.loads(log_path.read_text(encoding="utf-8"))
    assert data["stage"] == "code"
    assert data["topic"] == "Fourier Transform"
    assert data["duration_seconds"] == 0.45
    assert data["success"] is True
    assert data["preflight"]["valid"] is True
    assert data["repair"]["changes_count"] == 1
    assert data["artifacts"]["code"] == "class S(Scene): pass"

    last_run = store.get_last_run()
    assert last_run is not None
    assert last_run["run_id"] == data["run_id"]


def test_serialize_model_messages():
    """Verify that diverse message types are cleanly converted to JSON serializable objects."""
    messages = [
        {"role": "user", "content": "Explain math"},
        VideoClassifyResponse(animatable=True, subject="math", topic="Calculus", reason="Derivatives"),
    ]
    serialized = serialize_model_messages(messages)
    assert len(serialized) == 2
    assert serialized[0]["role"] == "user"
    assert serialized[1]["subject"] == "math"
    assert serialized[1]["topic"] == "Calculus"


def test_terminal_observer_render():
    """Verify terminal observer renders without exceptions."""
    console = Console(record=True, width=100)
    obs = HitlTerminalObserver(console=console, verbose=True)

    obs.banner("Test Banner", "Subtitle")
    obs.step("TEST", "Running unit test")
    obs.success("All systems green")
    obs.warning("Watch out for drift")
    obs.error("Simulated error")

    classify_res = VideoClassifyResponse(
        animatable=True, subject="math", topic="Eigenvalues", reason="Linear transformations"
    )
    obs.show_classification(classify_res, duration=0.12)
    obs.show_code("from manim import *\nclass S(Scene): pass", scene_name="S")
    obs.show_code_diff("a = 1", "a = 2", title="Test Diff")

    output = console.export_text()
    assert "Test Banner" in output
    assert "Eigenvalues" in output
    assert "All systems green" in output


@pytest.mark.anyio
async def test_mock_pipeline_all_stages(tmp_path: Path):
    """Verify that all pipeline stages execute end-to-end in offline mock mode without errors."""
    store = HitlRunStore(log_dir=tmp_path)
    console = Console(record=True, width=100)
    observer = HitlTerminalObserver(console=console)

    # Stage 1: Classify
    classification = await run_classify_stage(
        "Explain the Fourier Transform", observer, store, mock=True
    )
    assert classification.animatable is True
    assert classification.subject == "math"
    assert classification.topic == "Fourier Transform"

    # Stage 2: Compose
    plan = await run_compose_stage(
        "Text", classification.topic, observer, store, mock=True
    )
    assert "# Visualizing the Fourier Transform" in plan
    assert "## Scene 1:" in plan

    # Stage 3: Code
    code, scene_name = await run_code_stage(
        plan, classification.topic, observer, store, mock=True
    )
    assert "class FourierTransformScene(Scene):" in code
    assert scene_name == "FourierTransformScene"

    # Stage 5: Repair
    repaired_code, rep_scene = await run_repair_stage(
        code, "IndexError: list index out of range", scene_name, observer, store, mock=True
    )
    assert "FourierTransformScene" in repaired_code

    runs = store.list_runs()
    assert len(runs) >= 4
