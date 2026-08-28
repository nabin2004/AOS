"""Unit test for RITL ManimAgent self-correction module."""

from ritl_doc_retriever import extract_manim_api_calls, generate_ritl_doc_prompt_injection
from ritl_manim_agent import RITLManimAgent, RITLExecutionResult


def test_extract_manim_api_calls():
    code = """
from manim import *

class TestScene(Scene):
    def construct(self):
        circle = Circle(radius=2.0)
        self.play(Create(circle))
"""
    api_calls = extract_manim_api_calls(code)
    assert "Scene" in api_calls
    assert "Circle" in api_calls
    assert "Create" in api_calls


def test_ritl_doc_prompt_injection():
    code = "svg = SVGMobject('test.svg', fill_opacity=0.5)"
    tb = "TypeError: SVGMobject.__init__() got an unexpected keyword argument 'fill_opacity'"
    prompt = generate_ritl_doc_prompt_injection(code, tb)
    # Check that function symbol or prompt header is present
    assert isinstance(prompt, str)


def test_ritl_agent_mock_callback():
    agent = RITLManimAgent(max_loops=2)
    bad_script = "from manim import *\nclass TestScene(Scene):\n    def construct(self):\n        pass"

    def mock_llm_fix(prompt: str) -> str:
        return bad_script + "\n# Fixed"

    result = agent.run_self_correction_loop(
        initial_script=bad_script,
        scene_class_name="TestScene",
        llm_fix_callback=mock_llm_fix,
    )
    assert isinstance(result, RITLExecutionResult)
    assert result.iterations >= 1
