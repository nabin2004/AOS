"""Tests for local Ollama model settings auto-configuration and resolution."""

import os
from unittest.mock import patch

from educlaw.agent.factory import build_agent, resolve_educlaw_model
from educlaw.settings import Settings


def test_settings_auto_export_ollama_base_url():
    with patch.dict(os.environ, {"EDUCLAW_MODEL": "ollama:hf.co/nabin2004/AOS-qwen3-8b-narrated-sft-gguf"}, clear=True):
        settings = Settings.from_env()
        assert settings.model == "ollama:hf.co/nabin2004/AOS-qwen3-8b-narrated-sft-gguf"
        assert settings.ollama_base_url == "http://localhost:11434/v1"
        assert os.environ.get("OLLAMA_BASE_URL") == "http://localhost:11434/v1"


def test_resolve_educlaw_model_ollama():
    resolved = resolve_educlaw_model("ollama:hf.co/nabin2004/AOS-qwen3-8b-narrated-sft-gguf")
    assert not isinstance(resolved, str)
    assert hasattr(resolved, "model_name") or hasattr(resolved, "name") or type(resolved).__name__ == "OpenAIChatModel"


def test_build_agent_with_ollama_model():
    with patch.dict(os.environ, {"EDUCLAW_MODEL": "ollama:hf.co/nabin2004/AOS-qwen3-8b-narrated-sft-gguf", "OLLAMA_BASE_URL": "http://localhost:11434/v1"}):
        settings = Settings.from_env()
        agent = build_agent(settings, wrap_kitaru=False)
        assert agent is not None
        assert agent.name == "EduClaw"
