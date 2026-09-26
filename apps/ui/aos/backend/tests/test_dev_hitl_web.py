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
    assert "checkpoint_select_mode" in tool_names
    assert "checkpoint_approve_visual_plan" in tool_names
    assert "load_skill_reference" in tool_names
    assert "synthesize_manim_code" in tool_names
    assert "validate_code_with_lsp" in tool_names
    assert "repair_manim_code" in tool_names
    assert "generate_and_validate_manim_code" in tool_names
    assert "render_manim_scene" in tool_names
    assert "inspect_hitl_workspace" in tool_names
    assert "read_skill_reference" in tool_names
    assert "compile_marp_code" in tool_names

    # Verify that human checkpoints require operator approval
    assert tools["checkpoint_approve_classification"].requires_approval is True
    assert tools["checkpoint_select_mode"].requires_approval is True
    assert tools["checkpoint_approve_visual_plan"].requires_approval is True
    assert tools["render_manim_scene"].requires_approval is True

    # Verify that DeferredToolRequests is among output_types so deferred tool approval works
    from pydantic_ai import DeferredToolRequests
    assert DeferredToolRequests in agent._output_type


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


@pytest.mark.anyio
async def test_granular_streaming_tools(tmp_path: Path):
    """Verify granular tools for streaming skill load, code synthesis, LSP diagnostics, and repair."""
    ws = HitlWorkspace(workspace_dir=tmp_path)
    agent = create_hitl_web_agent(mock=True, workspace_dir=tmp_path)
    tools = agent._function_toolset.tools

    # 1. Test load_skill_reference
    skill_tool = tools["load_skill_reference"]
    skill_res = skill_tool.function(skill="manimce-best-practices")
    assert "manimce-best-practices" in skill_res

    # 2. Test synthesize_manim_code
    synth_tool = tools["synthesize_manim_code"]
    synth_res = await synth_tool.function(
        None,
        topic="QuickSort",
        plan_markdown="# QuickSort\n## Scene 1\n",
    )
    assert "synthesized successfully" in synth_res
    assert ws.scene_file.exists()

    # 3. Test validate_code_with_lsp
    val_tool = tools["validate_code_with_lsp"]
    val_res = val_tool.function(scene_name="FourierTransformScene")
    assert "Pyright LSP Validation Report" in val_res

    # 4. Test repair_manim_code
    repair_tool = tools["repair_manim_code"]
    repair_res = await repair_tool.function(
        None,
        error_feedback="NameError: name 'rect' is not defined",
        scene_name="FourierTransformScene",
    )
    assert "repaired successfully" in repair_res


def test_read_skill_reference_fuzzy_resolution(tmp_path: Path):
    """Verify that read_skill_reference resolves naked filenames and subpaths correctly."""
    agent = create_hitl_web_agent(mock=True, workspace_dir=tmp_path)
    tool = agent._function_toolset.tools["read_skill_reference"]

    # 1. Resolves narrative-patterns.md located in references/
    res1 = tool.function(path="narrative-patterns.md")
    assert "Narrative Arc Patterns" in res1 or "Narrative" in res1
    assert "File 'narrative-patterns.md' not found" not in res1

    # 2. Resolves visual-techniques.md located in references/
    res2 = tool.function(path="visual-techniques.md")
    assert "Visual Techniques" in res2 or "Techniques" in res2
    assert "File 'visual-techniques.md' not found" not in res2

    # 3. Resolves positioning.md located in rules/
    res3 = tool.function(path="positioning.md")
    assert "next_to" in res3 or "Positioning" in res3
    assert "File 'positioning.md' not found" not in res3

    # 4. Resolves exact relative path references/narrative-patterns.md
    res4 = tool.function(path="references/narrative-patterns.md")
    assert "Narrative" in res4

    # 5. Non-existent file returns helpful available references
    res_none = tool.function(path="totally-nonexistent-file.md")
    assert "Available reference files" in res_none


def test_checkpoint_resilient_parameters(tmp_path: Path):
    """Verify that checkpoint tools handle omitted optional fields, aliases, and string booleans."""
    ws = HitlWorkspace(workspace_dir=tmp_path)
    agent = create_hitl_web_agent(mock=True, workspace_dir=tmp_path)
    tools = agent._function_toolset.tools

    # 1. Classification with string animatable="true" and omitted topic/reason
    ws.save_input("Explain Euler's Formula", topic="Euler's Formula")
    classify_tool = tools["checkpoint_approve_classification"]
    res_cls = classify_tool.function(subject="math", animatable="true")
    assert "Classification confirmed by operator" in res_cls
    assert "Euler's Formula" in res_cls
    loaded_cls = ws.load_classification()
    assert loaded_cls["animatable"] is True
    assert loaded_cls["subject"] == "math"

    # 2. Visual plan with omitted subject and alias `plan` instead of `plan_markdown`
    plan_tool = tools["checkpoint_approve_visual_plan"]
    res_plan = plan_tool.function(
        topic="Euler's Formula",
        plan="# Scene 1: Euler Rotation\nContent here",
    )
    assert "Visual plan confirmed by operator for 'Euler's Formula'" in res_plan
    loaded_plan, plan_topic = ws.load_plan()
    assert "# Scene 1: Euler Rotation" in loaded_plan
    assert plan_topic == "Euler's Formula"


def test_checkpoint_select_mode_tool(tmp_path: Path):
    """Verify checkpoint_select_mode writes mode_selection.json and handles slide, animation, and scivis."""
    ws = HitlWorkspace(workspace_dir=tmp_path)
    agent = create_hitl_web_agent(mock=True, workspace_dir=tmp_path)
    tools = agent._function_toolset.tools

    # Pre-seed classification
    tools["checkpoint_approve_classification"].function(
        topic="Orbit Simulation",
        subject="physics",
        animatable=True,
        needs_3d=True,
    )

    mode_tool = tools["checkpoint_select_mode"]

    # 1. Select SciVis mode with libraries
    res_scivis = mode_tool.function(
        recommended_mode="scivis",
        reason="Scientific orbital simulation with astropy and scipy",
        scivis_libraries=["astropy", "scipy"],
        scivis_domain="astrophysics",
    )
    assert "Mode confirmed by operator: **SCIVIS**" in res_scivis
    assert "astropy, scipy" in res_scivis
    assert ws.mode_file.exists()

    loaded_mode = ws.load_mode_selection()
    assert loaded_mode is not None
    assert loaded_mode["mode"] == "scivis"
    assert loaded_mode["scivis_libraries"] == ["astropy", "scipy"]
    assert loaded_mode["uses_3d"] is True

    # 2. Select Slide mode
    res_slide = mode_tool.function(
        recommended_mode="slide",
        reason="Clean slide presentation with step-by-step proofs",
    )
    assert "Mode confirmed by operator: **SLIDE**" in res_slide
    loaded_mode2 = ws.load_mode_selection()
    assert loaded_mode2["mode"] == "slide"

    # 3. Select Marp mode
    res_marp = mode_tool.function(
        recommended_mode="marp",
        reason="Declarative slide deck with code and bullet items",
        marp_layout="hybrid",
    )
    assert "Mode confirmed by operator: **MARP**" in res_marp
    loaded_mode3 = ws.load_mode_selection()
    assert loaded_mode3["mode"] == "marp"
    assert loaded_mode3["marp_layout"] == "hybrid"


def test_compile_marp_code_tool(tmp_path: Path):
    """Verify compile_marp_code compiles Marp markdown and writes scene.py and presentation.marp.md."""
    ws = HitlWorkspace(workspace_dir=tmp_path)
    agent = create_hitl_web_agent(mock=True, workspace_dir=tmp_path)
    tools = agent._function_toolset.tools

    marp_text = (
        "---\nmarp: true\n---\n"
        "<!-- _class: title -->\n# Transformer Attention\n### Query Key Value\n\n"
        "---\n<!-- _class: bullets -->\n## Attention Steps\n- Scaled dot product\n- Softmax weights\n"
    )

    compile_tool = tools["compile_marp_code"]
    res = compile_tool.function(marp_markdown=marp_text, scene_name="AttentionScene")

    assert "Marp compiled deterministically" in res
    assert "AttentionScene" in res
    assert ws.scene_file.exists()
    assert ws.marp_file.exists()

    code_saved = ws.scene_file.read_text(encoding="utf-8")
    assert "class AttentionScene(Scene):" in code_saved
    assert "BulletedList" in code_saved


def test_inspect_hitl_workspace_tool(tmp_path: Path):
    """Verify inspect_hitl_workspace accurately lists artifacts including mode_selection."""
    ws = HitlWorkspace(workspace_dir=tmp_path)
    agent = create_hitl_web_agent(mock=True, workspace_dir=tmp_path)
    tools = agent._function_toolset.tools

    tools["checkpoint_approve_classification"].function(
        topic="Logarithms",
        subject="math",
        animatable=True,
    )
    tools["checkpoint_select_mode"].function(
        recommended_mode="animation",
        reason="Visual logarithmic scaling curve",
    )

    inspect_tool = tools["inspect_hitl_workspace"]
    status = inspect_tool.function()
    assert "mode_selection: EXISTS" in status
    assert "classification: EXISTS" in status



