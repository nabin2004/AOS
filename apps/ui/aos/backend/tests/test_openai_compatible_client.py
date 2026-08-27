"""Tests for custom OpenAI-compatible endpoint error mapping."""

from app.agents.openai_compatible_client import format_custom_endpoint_error, models_url


def test_models_url_strips_v1() -> None:
    assert (
        models_url("https://example--app.modal.direct/v1")
        == "https://example--app.modal.direct/v1/models"
    )
    assert (
        models_url("https://example--app.modal.direct/v1/")
        == "https://example--app.modal.direct/v1/models"
    )


def test_models_url_adds_v1_when_missing() -> None:
    assert models_url("https://host.example") == "https://host.example/v1/models"


def test_format_503_mentions_custom_endpoint() -> None:
    raw = "status_code: 503, model_name: aos-qwen2.5-coder-7b-manim, body:"
    out = format_custom_endpoint_error(
        raw, base_url="https://nabinoli2004--aos-qwen-coder-server-server.us-east.modal.direct/v1"
    )
    assert "HTTP 503" in out
    assert "Custom LLM endpoint is unavailable" in out
    assert "nabinoli2004--aos-qwen-coder-server" in out
    assert "Original:" in out


def test_format_503_is_idempotent() -> None:
    first = format_custom_endpoint_error("status_code: 503, body:")
    assert format_custom_endpoint_error(first) == first


def test_format_leaves_other_errors() -> None:
    msg = "compile_failed: SyntaxError"
    assert format_custom_endpoint_error(msg) == msg
