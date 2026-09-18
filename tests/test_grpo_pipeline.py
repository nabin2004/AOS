"""Comprehensive verification and unit test suite for AOS GRPO pipeline.
Tests config parsing, adapter resolution, ManiBench indexing, reward functions,
VLM judge parsing, stop tokens, and Manimator adapter integration.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

# Add apps/grpo and repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
GRPO_ROOT = REPO_ROOT / "apps" / "grpo"
sys.path.insert(0, str(GRPO_ROOT))
sys.path.insert(0, str(REPO_ROOT))

import unittest

from config import (
    DEFAULT_BASE_MODEL,
    DEFAULT_BETA,
    DEFAULT_LEARNING_RATE,
    TrainingConfig,
    apply_dual_t4_preset,
    apply_p100_preset,
    apply_rtx3060_preset,
    build_arg_parser,
)
from manibench import (
    GL_ONLY_PATTERNS,
    ProblemMeta,
    _extract_keywords,
    _patterns_for_event,
    format_user_prompt,
    get_alignment_events,
    get_coverage_terms,
    get_vcer_patterns,
)
from rewards import (
    REWARD_WEIGHTS,
    _extract_python,
    _has_manim_scene,
    _heuristic_exec_score,
    _length_penalty,
    _syntax_ok,
    combined_reward,
    coverage_reward,
    executability_reward,
    lexical_alignment_reward,
    narration_reward,
    vcer_reward,
)
from vlm_judge import parse_score_from_response
from trainer import KaggleTimeLimitCallback


class TestGRPOConfigAndManimator(unittest.TestCase):
    """Test CLI argument parsing and adapter configuration."""

    def test_default_qwen_config(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--base", "qwen"])
        config = TrainingConfig.from_cli(args)

        self.assertEqual(config.base_family, "qwen")
        self.assertEqual(config.base_model, "Qwen/Qwen3-8B")
        self.assertEqual(config.wandb_project, "aos-grpo")
        self.assertIn("qwen3-8b", config.wandb_tags)

    def test_manimator_adapter_configuration(self):
        """Verify that passing the new Manimator adapter correctly propagates through config."""
        parser = build_arg_parser()
        manimator_adapter = "nabin2004/qwen-Manimator-1-sft"
        args = parser.parse_args([
            "--base", "qwen",
            "--base-model", "Qwen/Qwen3-8B",
            "--sft-lora", manimator_adapter,
            "--run-name", "qwen-manimator-1-grpo",
            "--hub-repo", "nabin2004/qwen-Manimator-1-grpo",
            "--push-to-hub",
        ])
        config = TrainingConfig.from_cli(args)

        self.assertEqual(config.base_family, "qwen")
        self.assertEqual(config.base_model, "Qwen/Qwen3-8B")
        self.assertEqual(str(config.sft_lora_path), manimator_adapter)
        self.assertEqual(config.run_name, "qwen-manimator-1-grpo")
        self.assertEqual(config.hub_repo, "nabin2004/qwen-Manimator-1-grpo")
        self.assertTrue(config.push_to_hub)

    def test_dual_t4_preset(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--base", "qwen", "--dual-t4"])
        config = TrainingConfig.from_cli(args)

        self.assertEqual(config.num_generations, 4)
        self.assertEqual(config.policy_device, "cuda:0")
        self.assertEqual(config.reward_device, "cuda:1")
        self.assertEqual(config.vlm_judge, "ensemble")
        self.assertTrue(config.render)
        self.assertTrue(config.load_in_4bit)

    def test_p100_preset(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--base", "qwen", "--p100"])
        config = TrainingConfig.from_cli(args)

        self.assertEqual(config.num_generations, 2)
        self.assertEqual(config.max_prompt_length, 768)
        self.assertEqual(config.max_completion_length, 768)
        self.assertTrue(config.load_in_4bit)

    def test_rtx3060_preset(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--base", "qwen", "--rtx3060"])
        config = TrainingConfig.from_cli(args)

        self.assertEqual(config.num_generations, 2)
        self.assertEqual(config.max_prompt_length, 512)
        self.assertEqual(config.max_completion_length, 512)


class TestManiBenchLogic(unittest.TestCase):
    """Test ManiBench prompt formatting, keyword extraction, and metadata indexing."""

    def test_format_user_prompt(self):
        prompt = format_user_prompt("Create a Fourier transform visualization.")
        self.assertEqual(len(prompt), 1)
        self.assertEqual(prompt[0]["role"], "user")
        self.assertTrue(prompt[0]["content"].startswith("Write valid Manim Community Edition (CE) Python code."))
        self.assertIn("Create a Fourier transform visualization.", prompt[0]["content"])

    def test_extract_keywords(self):
        text = "The quick brown fox jumps over each and every lazy dog with circle"
        keywords = _extract_keywords(text, min_len=4)
        # Should exclude 'quick' (len 5, but let's check), 'brown', 'jumps', 'lazy', 'circle'
        # Should exclude stop words: 'the', 'each', 'every', 'with', 'and'
        self.assertNotIn("the", [k.lower() for k in keywords])
        self.assertNotIn("each", [k.lower() for k in keywords])
        self.assertNotIn("every", [k.lower() for k in keywords])
        self.assertNotIn("with", [k.lower() for k in keywords])
        self.assertIn("brown", [k.lower() for k in keywords])
        self.assertIn("circle", [k.lower() for k in keywords])

    def test_patterns_for_event(self):
        event = {
            "description": "Show axes with sine wave",
            "keyword_bank": ["Axes(", "FunctionGraph"],
        }
        patterns = _patterns_for_event(event)
        self.assertTrue(any("Axes" in p for p in patterns))
        self.assertTrue(any("FunctionGraph" in p for p in patterns))


class TestRewardFunctions(unittest.TestCase):
    """Test all reward metrics and edge cases."""

    def test_extract_python(self):
        # 1. Closed fence
        code1 = "Here is the code:\n```python\nfrom manim import *\nclass S(Scene):\n    pass\n```\nEnjoy!"
        extracted1 = _extract_python(code1)
        self.assertIn("class S(Scene):", extracted1)
        self.assertNotIn("```", extracted1)

        # 2. Unclosed fence (truncated completion)
        code2 = "```python\nfrom manim import *\nclass S(Scene):\n    def construct(self):\n        c = Circle()"
        extracted2 = _extract_python(code2)
        self.assertIn("c = Circle()", extracted2)
        self.assertNotIn("```", extracted2)

        # 3. Thinking tags stripped
        code3 = "<think>Let me write the code.</think>\n```python\nclass S(Scene):\n    pass\n```"
        extracted3 = _extract_python(code3)
        self.assertNotIn("<think>", extracted3)
        self.assertIn("class S(Scene):", extracted3)

    def test_has_manim_scene(self):
        valid = "from manim import *\nclass MyScene(Scene):\n    def construct(self): pass"
        voiceover = "from manim_voiceover import VoiceoverScene\nclass Lecture(VoiceoverScene):\n    pass"
        threed = "class Visual(ThreeDScene):\n    pass"
        invalid = "class DataProcessor:\n    def run(self): pass"

        self.assertTrue(_has_manim_scene(valid))
        self.assertTrue(_has_manim_scene(voiceover))
        self.assertTrue(_has_manim_scene(threed))
        self.assertFalse(_has_manim_scene(invalid))

    def test_syntax_ok(self):
        self.assertTrue(_syntax_ok("x = 1 + 2"))
        self.assertFalse(_syntax_ok("x = 1 + (def foo"))

    def test_executability_reward_heuristic(self):
        valid_code = (
            "```python\n"
            "from manim import *\n"
            "class Demo(Scene):\n"
            "    def construct(self):\n"
            "        c = Circle()\n"
            "        self.play(Create(c))\n"
            "```"
        )
        broken_code = "```python\nclass Demo(Scene):\n    def construct(self):\n        c = "
        rubbish = "Hello, I cannot answer this request."

        os.environ["MANIBENCH_GRPO_RENDER"] = "0"
        scores = executability_reward([valid_code, broken_code, rubbish])

        # Valid code should get highest score
        self.assertGreater(scores[0], scores[1])
        self.assertGreater(scores[1], scores[2])
        self.assertGreaterEqual(scores[0], 0.70)
        self.assertLessEqual(scores[2], 0.10)

    def test_vcer_reward(self):
        # Manim CE code (clean)
        clean_code = "from manim import *\nclass S(Scene):\n    def construct(self):\n        self.play(Create(Circle()))"
        # ManimGL / deprecated code
        gl_code = "from manimlib import *\nclass S(GraphScene):\n    def construct(self):\n        self.play(ShowCreation(Circle()))\n        t = TexMobject('x')"

        rewards = vcer_reward([clean_code, gl_code])
        self.assertEqual(rewards[0], 1.0)
        self.assertLess(rewards[1], 1.0)

    def test_narration_reward(self):
        full_narrated = (
            "from manim import *\n"
            "from manim_voiceover import VoiceoverScene\n"
            "from manim_voiceover.services.recorder import RecorderService\n"
            "class MyLecture(VoiceoverScene):\n"
            "    def construct(self):\n"
            "        self.set_speech_service(RecorderService())\n"
            "        with self.voiceover(text='Welcome') as tracker:\n"
            "            self.play(Create(Circle()))\n"
        )
        no_narration = "class S(Scene):\n    def construct(self):\n        self.play(Create(Circle()))"

        rewards = narration_reward([full_narrated, no_narration])
        self.assertEqual(rewards[0], 1.0)
        self.assertEqual(rewards[1], 0.0)

    def test_coverage_reward(self):
        code_with_terms = (
            "class S(Scene):\n"
            "    def construct(self):\n"
            "        t = MathTex('E=mc^2')\n"
            "        t.set_color(RED)\n"
            "        ax = Axes()\n"
            "        vg = VGroup(t, ax)\n"
            "        self.play(Write(vg))\n"
        )
        rewards = coverage_reward([code_with_terms], problem_id=["unknown_problem"])
        self.assertGreater(rewards[0], 0.0)

    def test_combined_reward_weights_and_damping(self):
        valid_code = (
            "```python\n"
            "from manim import *\n"
            "from manim_voiceover import VoiceoverScene\n"
            "class S(VoiceoverScene):\n"
            "    def construct(self):\n"
            "        self.set_speech_service(AOSSpeechService())\n"
            "        with self.voiceover(text='Hello') as trk:\n"
            "            self.play(Create(Circle()))\n"
            "```"
        )
        non_code = "Just plain text without any code."

        os.environ["MANIBENCH_GRPO_RENDER"] = "0"
        os.environ["MANIBENCH_GRPO_CLIP_REWARD"] = "0"
        scores = combined_reward([valid_code, non_code], completion_ids=[[1]*50, [1]*20])

        self.assertGreater(scores[0], scores[1])
        self.assertGreater(scores[0], 0.5)
        self.assertLess(scores[1], 0.1)


class TestVLMJudgeParsing(unittest.TestCase):
    """Test score parser in VLM judge."""

    def test_fraction_parsing(self):
        self.assertEqual(parse_score_from_response("I give this 4/5"), 0.8)
        self.assertEqual(parse_score_from_response("Score: 9/10"), 0.9)
        self.assertEqual(parse_score_from_response("Rating: 5/5"), 1.0)
        self.assertEqual(parse_score_from_response("0/5"), 0.0)

    def test_decimal_parsing(self):
        self.assertEqual(parse_score_from_response("Score: 0.85"), 0.85)
        self.assertEqual(parse_score_from_response("rating = 0.92"), 0.92)
        self.assertEqual(parse_score_from_response("0.7"), 0.7)

    def test_keyword_fallbacks(self):
        self.assertEqual(parse_score_from_response("yes, accurate"), 0.9)
        self.assertEqual(parse_score_from_response("fail, blank screen"), 0.1)
        self.assertEqual(parse_score_from_response(""), 0.5)


class TestKaggleTimeLimit(unittest.TestCase):
    """Test Kaggle time limit callback."""

    def test_callback_triggers_stop(self):
        cb = KaggleTimeLimitCallback(max_hours=0.0)  # 0 hours -> elapsed >= 0
        from unittest.mock import MagicMock
        control = MagicMock()
        control.should_save = False
        control.should_training_stop = False

        cb.on_step_end(MagicMock(), MagicMock(), control)
        self.assertTrue(control.should_save)
        self.assertTrue(control.should_training_stop)


if __name__ == "__main__":
    unittest.main()
