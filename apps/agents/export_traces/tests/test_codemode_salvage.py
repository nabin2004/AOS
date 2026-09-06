"""Unit tests for CodeMode bare Manim auto-salvage and resilient compilation."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolReturn

from codemode_retry import install_codemode_retry_patch
from agent_graph import _salvage_codemode_text_dump
from tools.coder_workspace import load_manifest, save_manifest

SAMPLE_BARE_MANIM = """
from manim import *
from aos_manim_slides import VoiceoverSlideScene
from tools.aos_speech_service import AOSSpeechService

class BODMASScene(VoiceoverSlideScene):
    def construct(self):
        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))
        eq = MathTex(r"2 + 3 \\times 4")
        with self.voiceover(text="BODMAS states that multiplication comes before addition.") as tracker:
            self.play(Write(eq), run_time=tracker.duration)
"""


@pytest.mark.asyncio
async def test_codemode_bare_manim_auto_salvage(tmp_path: Path):
    install_codemode_retry_patch()
    from pydantic_ai_harness.code_mode import _toolset
    from pydantic_ai.toolsets import FunctionToolset

    toolset_instance = _toolset.CodeModeToolset(FunctionToolset([]))
    
    with patch("tools.manim_write.manim_write") as mock_write, \
         patch("tools.compile.compile_manim_code") as mock_compile:
        
        mock_write.return_value = {"ok": True, "scene_file": "scene.py"}
        mock_compile.return_value = {"ok": True, "video_path": "/fake/video.mp4"}
        
        res = await toolset_instance.call_tool(
            "run_code",
            {"code": SAMPLE_BARE_MANIM},
            MagicMock(),
            MagicMock(),
        )
        
        assert isinstance(res, ToolReturn)
        assert res.return_value == {"ok": True, "video_path": "/fake/video.mp4"}
        assert mock_write.called
        assert mock_compile.called


@pytest.mark.asyncio
async def test_codemode_invalid_syntax_guidance():
    install_codemode_retry_patch()
    from pydantic_ai_harness.code_mode import _toolset
    from pydantic_ai.toolsets import FunctionToolset

    toolset_instance = _toolset.CodeModeToolset(FunctionToolset([]))
    ctx = MagicMock()
    tools = await toolset_instance.get_tools(ctx)
    run_code_tool = tools["run_code"]
    
    with pytest.raises(ModelRetry) as exc_info:
        await toolset_instance.call_tool(
            "run_code",
            {"code": "def invalid_python(((:): pass"},
            ctx,
            run_code_tool,
        )
    
    err_msg = str(exc_info.value)
    assert "CodeMode Format Guide" in err_msg or "Syntax error" in err_msg


def test_salvage_uncompiled_scene_file(tmp_path: Path):
    scene_file = tmp_path / "scene.py"
    scene_file.write_text(SAMPLE_BARE_MANIM, encoding="utf-8")
    
    manifest = {
        "output_dir": str(tmp_path),
        "scene_file": "scene.py",
        "last_compile": {"ok": False},
        "last_write": {"ok": True, "scene_name": "BODMASScene"},
    }
    save_manifest(tmp_path, manifest)
    
    with patch("tools.compile.compile_manim_code") as mock_compile:
        mock_compile.return_value = {"ok": True}
        _salvage_codemode_text_dump(tmp_path, summary="error: timeout", messages=None)
        
        assert mock_compile.called
        call_kwargs = mock_compile.call_args.kwargs
        assert call_kwargs["scene_name"] == "BODMASScene"
        assert str(call_kwargs["output_dir"]) == str(tmp_path)
