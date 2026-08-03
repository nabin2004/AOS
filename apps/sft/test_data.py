"""Tests for dataset loading helpers."""

from data import extract_user_prompt


def test_extract_user_prompt_from_messages():
    sample = {
        "messages": [
            {"role": "system", "content": "You write Manim code."},
            {"role": "user", "content": "Draw a red circle."},
            {"role": "assistant", "content": "from manim import *\n..."},
        ]
    }
    assert extract_user_prompt(sample) == "Draw a red circle."


def test_extract_user_prompt_legacy_trajectory():
    sample = {"user_prompt": "Animate gradient descent."}
    assert extract_user_prompt(sample) == "Animate gradient descent."


def test_extract_user_prompt_fallback_prompt_field():
    sample = {"prompt": "Show a sine wave."}
    assert extract_user_prompt(sample) == "Show a sine wave."


def test_extract_user_prompt_empty():
    assert extract_user_prompt({}) == ""
