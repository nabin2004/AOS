import asyncio
import os
from pathlib import Path
import sys
import tempfile
import pytest

# Ensure apps/agents is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from error_classifier import ErrorCategory, classify_error
from llm_retry import execute_with_llm_retry
from tools.compile import validate_manim_code_static
from video_validator import validate_video_file
from code_repair import build_repair_prompt, extract_python_code


# -----------------------------------------------------------------------------
# 1. Error Classification Tests
# -----------------------------------------------------------------------------
def test_classify_503_cold_start():
    error_str = "httpx.HTTPStatusError: Server error '503 Service Unavailable' for url 'https://modal.com/v1/chat'"
    res = classify_error(error_str)
    assert res.category == ErrorCategory.TRANSIENT_LLM_ERROR
    assert res.is_retryable is True
    assert "Starting the AI model" in res.user_message
    assert "503" not in res.user_message  # Raw status hidden from user message


def test_classify_rate_limit_429():
    error_str = "HTTP 429 Too Many Requests: Rate limit reached for tokens per minute"
    res = classify_error(error_str)
    assert res.category == ErrorCategory.RATE_LIMIT
    assert res.is_retryable is True
    assert "rate limit" in res.user_message.lower() or "busy" in res.user_message.lower()


def test_classify_authentication_401():
    error_str = "HTTP 401 Unauthorized: Invalid API key provided"
    res = classify_error(error_str)
    assert res.category == ErrorCategory.AUTHENTICATION_ERROR
    assert res.is_retryable is False
    assert "authentication failed" in res.user_message.lower()


def test_classify_network_connection_reset():
    error_str = "httpx.ConnectError: [Errno 104] Connection reset by peer"
    res = classify_error(error_str)
    assert res.category == ErrorCategory.NETWORK_ERROR
    assert res.is_retryable is True


def test_classify_syntax_error():
    error_str = "SyntaxError: unexpected EOF while parsing line 42"
    res = classify_error(error_str)
    assert res.category == ErrorCategory.CODE_VALIDATION_ERROR
    assert res.is_repairable is True


def test_classify_manim_render_error():
    error_str = "LaTeX Error: File `standalone.cls' not found."
    res = classify_error(error_str)
    assert res.category == ErrorCategory.MANIM_RENDER_ERROR
    assert res.is_repairable is True


def test_classify_video_validation_error():
    error_str = "video_validation_failed: Video file is too small (0 bytes < 1024 threshold)"
    res = classify_error(error_str)
    assert res.category == ErrorCategory.VIDEO_VALIDATION_ERROR
    assert res.is_repairable is True


def test_classify_context_length_error():
    error_str = "This model's maximum context length is 32768 tokens. However, you requested 0 output tokens and your prompt contains at least 32769 input tokens."
    res = classify_error(error_str)
    assert res.category == ErrorCategory.CONTEXT_LENGTH_ERROR
    assert "context" in res.user_message.lower()


def test_repair_prompt_truncation():
    giant_traceback = "Traceback error line...\n" * 1000  # > 20,000 chars
    prompt = build_repair_prompt(
        original_prompt="Explain Fourier Transform",
        broken_code="from manim import *",
        traceback=giant_traceback,
        attempt=1,
        max_attempts=3,
    )
    assert len(prompt) < 15000
    assert "intermediate compiler logs truncated for context budget" in prompt



# -----------------------------------------------------------------------------
# 2. LLM Cold Start & Transient Retry Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_llm_retry_recovers_from_503():
    attempts = 0

    async def flaky_503_call():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("HTTP 503 Service Unavailable: Container booting")
        return "Model response: Success"

    progress_events = []

    def on_progress(stage, msg):
        progress_events.append((stage, msg))

    res = await execute_with_llm_retry(
        flaky_503_call,
        operation_name="Flaky Test Call",
        max_retries=4,
        on_progress=on_progress,
    )

    assert res == "Model response: Success"
    assert attempts == 3
    assert len(progress_events) == 2
    assert progress_events[0][0] == "LLM_COLD_START"


@pytest.mark.asyncio
async def test_llm_retry_fails_on_unauthorized():
    attempts = 0

    async def auth_fail_call():
        nonlocal attempts
        attempts += 1
        raise RuntimeError("HTTP 401 Unauthorized: Invalid API key")

    with pytest.raises(RuntimeError) as exc_info:
        await execute_with_llm_retry(
            auth_fail_call,
            operation_name="Auth Test Call",
            max_retries=3,
        )

    assert attempts == 1  # Should not retry 401
    assert "401" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 3. Static AST & Sanity Validation Tests
# -----------------------------------------------------------------------------
def test_static_validation_valid_code():
    code = '''
from manim import *
from aos_manim_slides import VoiceoverSlideScene
from tools.aos_speech_service import AOSSpeechService

class DemoScene(VoiceoverSlideScene):
    def construct(self):
        self.set_speech_service(AOSSpeechService(voice="alba"))
        with self.voiceover(text="Welcome to this animation.") as tracker:
            self.play(FadeIn(Circle()), run_time=tracker.duration)
'''
    valid, err = validate_manim_code_static(code, "DemoScene")
    assert valid is True
    assert err is None


def test_static_validation_syntax_error():
    broken_code = "class BrokenScene(Scene:\n    def construct(self): pass"
    valid, err = validate_manim_code_static(broken_code, "BrokenScene")
    assert valid is False
    assert err is not None
    assert "syntax_error" in err


def test_static_validation_missing_scene():
    code = "import math\nprint(math.sqrt(16))"
    valid, err = validate_manim_code_static(code, "Scene")
    assert valid is False
    assert "no_scene_class_found" in err


def test_static_validation_run_code_recursion():
    code = "await run_code('from manim import *')"
    valid, err = validate_manim_code_static(code, "Scene")
    assert valid is False
    assert "invalid_call" in err


# -----------------------------------------------------------------------------
# 4. Video Validation Tests
# -----------------------------------------------------------------------------
def test_video_validation_missing_file():
    res = validate_video_file("non_existent_video_path.mp4")
    assert res.ok is False
    assert "does not exist" in (res.error or "")


def test_video_validation_zero_byte_file():
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        temp_path = Path(f.name)
    try:
        res = validate_video_file(temp_path, min_bytes=1024)
        assert res.ok is False
        assert "too small" in (res.error or "")
    finally:
        temp_path.unlink(missing_ok=True)


def test_video_validation_atom_fallback():
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        # Write valid MP4 ftyp header with padding > 1024 bytes
        f.write(b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2avc1mp41" + b"\x00" * 2000)
        temp_path = Path(f.name)
    try:
        res = validate_video_file(temp_path, min_bytes=1024)
        assert res.ok is True
        assert res.file_size_bytes > 1024
    finally:
        temp_path.unlink(missing_ok=True)


# -----------------------------------------------------------------------------
# 5. Code Repair Prompt & Extraction Tests
# -----------------------------------------------------------------------------
def test_extract_python_code_markdown():
    wrapped = "Here is your fixed code:\n```python\nfrom manim import *\nclass S(Scene): pass\n```\nHope this helps!"
    clean = extract_python_code(wrapped)
    assert clean == "from manim import *\nclass S(Scene): pass"


def test_build_repair_prompt_contains_all_context():
    prompt = build_repair_prompt(
        original_prompt="Explain Euler's identity",
        broken_code="self.play(WrongMethod())",
        traceback="AttributeError: 'Scene' object has no attribute 'WrongMethod'",
        attempt=2,
        max_attempts=3,
        scene_name="EulerScene",
    )
    assert "Euler's identity" in prompt
    assert "Attempt 2 of 3" in prompt
    assert "WrongMethod" in prompt
    assert "EulerScene" in prompt
