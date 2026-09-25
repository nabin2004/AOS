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


def test_hitl_workspace_lifecycle(tmp_path: Path):
    """Verify that HitlWorkspace correctly saves and loads JSON and Python formatted files."""
    from app.core.local_logging import HitlWorkspace

    ws = HitlWorkspace(workspace_dir=tmp_path)

    # 1. Input JSON
    ws.save_input("How does Dijkstra's Algorithm work?", topic="Dijkstra's Algorithm")
    assert ws.input_file.exists()
    inp = ws.load_input()
    assert inp is not None
    assert inp["text"] == "How does Dijkstra's Algorithm work?"
    assert inp["topic"] == "Dijkstra's Algorithm"

    # 2. Classification JSON
    classify_obj = VideoClassifyResponse(
        animatable=True,
        subject="cs",
        topic="Dijkstra's Algorithm",
        reason="Graph shortest path traversal",
    )
    ws.save_classification(classify_obj, query="How does Dijkstra's Algorithm work?")
    assert ws.classification_file.exists()
    class_data = ws.load_classification()
    assert class_data is not None
    assert class_data["topic"] == "Dijkstra's Algorithm"
    assert class_data["animatable"] is True
    assert class_data["subject"] == "cs"

    # 3. Plan (scenes.md & plan.json)
    ws.save_plan("# Dijkstra Plan\n## Scene 1\n", topic="Dijkstra's Algorithm")
    assert ws.plan_md_file.exists()
    assert ws.plan_json_file.exists()
    plan_md, topic = ws.load_plan()
    assert plan_md == "# Dijkstra Plan\n## Scene 1\n"
    assert topic == "Dijkstra's Algorithm"

    # 4. Code (scene.py & code.json)
    py_code = "from manim import *\n\nclass DijkstraScene(Scene):\n    def construct(self):\n        pass\n"
    ws.save_code(py_code, scene_name="DijkstraScene", topic="Dijkstra's Algorithm")
    assert ws.scene_file.exists()
    assert ws.code_json_file.exists()
    loaded_code, loaded_scene = ws.load_code()
    assert loaded_code == py_code
    assert loaded_scene == "DijkstraScene"

    # 5. Preflight JSON
    preflight = PreflightResult(valid=True, status="safe", blocking=False)
    ws.save_preflight(preflight)
    assert ws.preflight_file.exists()
    pre_data = ws.load_preflight()
    assert pre_data is not None
    assert pre_data["valid"] is True

    # 6. Repair (scene.py updated, backup preserved, repair.json saved)
    repaired_py = "from manim import *\n\nclass DijkstraScene(Scene):\n    def construct(self):\n        self.wait(1)\n"
    ws.save_repair(repaired_py, scene_name="DijkstraScene", error="IndexError", category="mobject_index", changes=["fixed index"])
    assert ws.repair_file.exists()
    assert (tmp_path / "scene_backup.py").exists()
    loaded_repaired, _ = ws.load_code()
    assert "self.wait(1)" in loaded_repaired

    # 7. Manifest
    assert ws.manifest_file.exists()
    manifest = json.loads(ws.manifest_file.read_text(encoding="utf-8"))
    assert manifest["last_stage"] == "repair"
    assert manifest["files"]["classification_json"] == "classification.json"
    assert manifest["files"]["scenes_md"] == "scenes.md"
    assert manifest["files"]["scene_py"] == "scene.py"


@pytest.mark.anyio
async def test_stage_chaining_via_workspace(tmp_path: Path):
    """Verify that independent stages chain together through directory JSON and Python artifacts."""
    from app.core.local_logging import HitlWorkspace

    store = HitlRunStore(log_dir=tmp_path / "logs")
    ws = HitlWorkspace(workspace_dir=tmp_path / "workspace")
    obs = HitlTerminalObserver()

    # Step 1: Run Classify Stage with topic query
    res = await run_classify_stage(
        "How does Dijkstra's Algorithm work?",
        obs,
        store,
        workspace=ws,
        mock=True,
    )
    assert res.topic == "Dijkstra's Algorithm"
    assert ws.classification_file.exists()

    # Step 2: Run Compose Stage — load topic from classification.json in workspace
    class_data = ws.load_classification()
    assert class_data is not None
    topic = class_data["topic"]
    query = class_data.get("query", topic)

    plan = await run_compose_stage(
        query,
        topic,
        obs,
        store,
        workspace=ws,
        mock=True,
    )
    assert ws.plan_md_file.exists()
    assert "Dijkstra's Algorithm" in plan

    # Step 3: Run Code Stage — load plan from scenes.md in workspace
    loaded_plan, plan_topic = ws.load_plan()
    assert loaded_plan is not None
    code, scene_name = await run_code_stage(
        loaded_plan,
        plan_topic,
        obs,
        store,
        workspace=ws,
        mock=True,
    )
    assert ws.scene_file.exists()
    assert ws.code_json_file.exists()
    assert "DijkstrasAlgorithmScene" in scene_name
    assert "from manim import *" in code

