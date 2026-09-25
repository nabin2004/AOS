"""Unit tests for dev_hitl_web.py — Pydantic AI Web Chat UI and Tool Approvals."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from app.core.local_logging import HitlWorkspace
from dev_hitl_web import (
    create_hitl_web_agent,
    create_hitl_web_app,
)


def test_create_hitl_web_agent_tools(tmp_path: Path):
    """Verify that hitl_web_agent is configured with native approval checkpoints."""
    agent = create_hitl_web_agent(mock=True, workspace_dir=tmp_path)
    
    # Check registered tool names
    tools = agent._function_toolset.tools
    tool_names = set(tools.keys())

    assert "checkpoint_approve_classification" in tool_names
    assert "checkpoint_approve_visual_plan" in tool_names
    assert "generate_and_validate_manim_code" in tool_names
    assert "render_manim_scene" in tool_names
    assert "inspect_hitl_workspace" in tool_names
    assert "read_skill_reference" in tool_names

    # Verify that human checkpoints require operator approval
    assert tools["checkpoint_approve_classification"].requires_approval is True
    assert tools["checkpoint_approve_visual_plan"].requires_approval is True
    assert tools["render_manim_scene"].requires_approval is True


def test_create_hitl_web_app_endpoints(tmp_path: Path):
    """Verify Starlette ASGI application health and configuration routes."""
    app = create_hitl_web_app(mock=True, workspace_dir=tmp_path)
    client = TestClient(app, base_url="http://127.0.0.1:7932")

    # 1. Health check
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json() == {"ok": True}

    # 2. Configuration endpoint
    res_cfg = client.get("/api/configure")
    assert res_cfg.status_code == 200
    cfg = res_cfg.json()
    assert "models" in cfg

    # 3. Main Web Chat UI index HTML
    res_ui = client.get("/")
    assert res_ui.status_code == 200
    assert "text/html" in res_ui.headers.get("content-type", "")


def test_checkpoint_approve_classification_tool(tmp_path: Path):
    """Verify checkpoint_approve_classification writes structured classification.json to workspace."""
    ws = HitlWorkspace(workspace_dir=tmp_path)
    agent = create_hitl_web_agent(mock=True, workspace_dir=tmp_path)

    tool = agent._function_toolset.tools["checkpoint_approve_classification"]
    # Execute the underlying tool function
    result = tool.function(
        topic="Logarithms",
        subject="math",
        animatable=True,
        reason="Exponential curves and logarithmic scales",
    )

    assert "Classification confirmed by operator" in result
    assert "Logarithms" in result
    assert "math" in result

    assert ws.classification_file.exists()
    data = json.loads(ws.classification_file.read_text(encoding="utf-8"))
    assert data["topic"] == "Logarithms"
    assert data["subject"] == "math"
    assert data["animatable"] is True


def test_checkpoint_approve_visual_plan_tool(tmp_path: Path):
    """Verify checkpoint_approve_visual_plan writes scenes.md and plan.json to workspace."""
    ws = HitlWorkspace(workspace_dir=tmp_path)
    agent = create_hitl_web_agent(mock=True, workspace_dir=tmp_path)

    tool = agent._function_toolset.tools["checkpoint_approve_visual_plan"]
    plan_text = "# Visualizing Logarithms\n## Scene 1\n"
    result = tool.function(
        topic="Logarithms",
        subject="math",
        plan_markdown=plan_text,
    )

    assert "Visual plan confirmed by operator" in result
    assert ws.plan_md_file.exists()
    assert ws.plan_json_file.exists()
    loaded_plan, topic = ws.load_plan()
    assert loaded_plan == plan_text
    assert topic == "Logarithms"


@pytest.mark.anyio
async def test_generate_and_validate_manim_code_tool(tmp_path: Path):
    """Verify code synthesis, LSP diagnostics, and workspace persistence in mock mode."""
    ws = HitlWorkspace(workspace_dir=tmp_path)
    agent = create_hitl_web_agent(mock=True, workspace_dir=tmp_path)

    tool = agent._function_toolset.tools["generate_and_validate_manim_code"]
    plan_text = "# Visualizing Fourier Transform\n## Scene 1\n"
    result = await tool.function(
        None,
        topic="Fourier Transform",
        plan_markdown=plan_text,
    )

    assert "Manim code synthesized and verified" in result
    assert "FourierTransformScene" in result
    assert ws.scene_file.exists()
    assert ws.code_json_file.exists()

    code, scene = ws.load_code()
    assert "FourierTransformScene" in code
    assert scene == "FourierTransformScene"
