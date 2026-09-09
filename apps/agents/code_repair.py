"""Self-healing Manim code repair loop.

When a generated Manim script fails static validation, runtime compilation,
or video validation, this module extracts the traceback and compiler diagnostics,
builds a targeted repair prompt, and requests a minimal root-cause fix from the model.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
import re
import shutil
import sys
from typing import Any

from pydantic_ai import Agent

from error_classifier import ErrorCategory, classify_error
from llm_config import model_for_agent, settings_for
from llm_retry import execute_with_llm_retry
from reliability_config import CODE_REPAIR_MAX_ATTEMPTS
from tools.compile import compile_manim_code, validate_manim_code_static
from video_validator import validate_video_file

logger = logging.getLogger(__name__)


REPAIR_SYSTEM_PROMPT = """You are an expert Manim code repair agent.
Your mission is to fix broken Manim Community Edition animation code that failed compilation, rendering, or output validation.

RULES:
1. Preserve the user's original pedagogical goal and scene structure.
2. Fix ONLY the root cause of the error.
3. Return the COMPLETE executable Python script.
   NEVER truncate code or use placeholders like "... remaining code unchanged ...".
4. Ensure the scene subclasses `VoiceoverSlideScene` or `VoiceoverScene` and contains `self.set_speech_service(...)`.
5. If LaTeX fails (e.g. LaTeX Error or standalone.cls), replace MathTex with simple Tex or Text to guarantee compilation.
6. Check all coordinates: keep visuals inside |x| <= 6.5, |y| <= 3.5.
7. Wrap your entire code in a ```python ... ``` markdown code block. Do NOT include commentary outside the code block.
"""

_repair_agent: Agent | None = None


def get_repair_agent() -> Agent:
    """Lazily instantiate the repair agent to avoid premature LLM provider initialization."""
    global _repair_agent
    if _repair_agent is None:
        _repair_agent = Agent(
            model_for_agent("coder"),
            name="Manim Repair Agent",
            description="Repairs broken Manim scripts based on compiler tracebacks and diagnostics.",
            system_prompt=REPAIR_SYSTEM_PROMPT,
            model_settings=settings_for("coder"),
        )
    return _repair_agent


@dataclass
class RepairResult:
    ok: bool
    video_path: str | None = None
    scene_path: str | None = None
    attempts_made: int = 0
    final_error: str | None = None
    repaired_code: str | None = None


def extract_python_code(text: str) -> str:
    """Extract clean Python code from markdown code fences if present."""
    if not text:
        return ""
    code_match = re.search(r"```(?:python)?\s*\n(.*?)\n```", text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    return text.strip()


def build_repair_prompt(
    *,
    original_prompt: str,
    broken_code: str,
    traceback: str,
    attempt: int,
    max_attempts: int,
    scene_name: str | None = None,
) -> str:
    """Build a comprehensive context for the repair model."""
    safe_traceback = str(traceback).strip()
    if len(safe_traceback) > 8000:
        safe_traceback = (
            safe_traceback[:3000]
            + "\n\n... [intermediate compiler logs truncated for context budget] ...\n\n"
            + safe_traceback[-5000:]
        )

    safe_code = str(broken_code).strip()
    if len(safe_code) > 20000:
        safe_code = safe_code[:20000] + "\n# ... [code truncated to prevent context overflow]"

    return f"""The following Manim scene failed to compile or validate (Attempt {attempt} of {max_attempts}).

=== ORIGINAL USER GOAL ===
{original_prompt}

=== FAILED SCENE NAME ===
{scene_name or 'Scene'}

=== COMPILER DIAGNOSTIC / TRACEBACK ===
{safe_traceback}

=== BROKEN SOURCE CODE ===
```python
{safe_code}
```

=== REPAIR INSTRUCTIONS ===
1. Analyze the exact error above.
2. Fix the broken imports, syntax errors, or invalid Manim API calls.
3. If LaTeX/standalone.cls failed, replace complex formulas with Text objects.
4. Output the complete, working Python file. Do not use placeholders or comments replacing code.
"""


async def run_manim_repair_loop(
    *,
    original_prompt: str,
    broken_code: str,
    error_summary: str,
    run_dir: str | Path,
    scene_name: str = "Scene",
    max_attempts: int = CODE_REPAIR_MAX_ATTEMPTS,
) -> RepairResult:
    """Run an iterative self-healing repair loop up to max_attempts."""
    workspace = Path(run_dir)
    current_code = broken_code
    current_error = error_summary

    for attempt in range(1, max_attempts + 1):
        progress_msg = f"AOS is fixing the animation code automatically… (Repair attempt {attempt} of {max_attempts})"
        print(f"-> CODE_REPAIRING {progress_msg}", file=sys.stderr, flush=True)

        # Isolated directory for this attempt
        attempt_dir = workspace / f"repair_attempt_{attempt}"
        attempt_dir.mkdir(parents=True, exist_ok=True)

        repair_prompt = build_repair_prompt(
            original_prompt=original_prompt,
            broken_code=current_code,
            traceback=current_error,
            attempt=attempt,
            max_attempts=max_attempts,
            scene_name=scene_name,
        )

        try:
            # Wrap repair model execution with LLM cold-start/transient retry
            async def _call_repair() -> str:
                res = await get_repair_agent().run(repair_prompt)
                return str(res.output) if res.output is not None else ""

            raw_output = await execute_with_llm_retry(
                _call_repair,
                operation_name=f"Manim Code Repair (Attempt {attempt})",
            )
            candidate_code = extract_python_code(raw_output)
            if not candidate_code:
                current_error = "Repair model returned empty code."
                continue

            current_code = candidate_code

            # 1. Static pre-validation
            print(f"-> VALIDATING_CODE Validating repaired code syntax (attempt {attempt})…", file=sys.stderr, flush=True)
            valid_static, static_err = validate_manim_code_static(current_code, scene_name)
            if not valid_static and static_err:
                current_error = f"Static validation failed after repair: {static_err}"
                logger.warning("Attempt %d repair produced invalid AST: %s", attempt, static_err)
                continue

            # 2. Re-compile
            print(f"-> RENDERING Rendering repaired scene (attempt {attempt})…", file=sys.stderr, flush=True)
            compile_raw = compile_manim_code(
                code=current_code,
                scene_name=scene_name,
                output_dir=str(attempt_dir),
            )
            try:
                compile_data = json.loads(compile_raw)
            except Exception:
                compile_data = {}

            if not compile_data.get("ok"):
                current_error = (
                    compile_data.get("failure_marker")
                    or compile_data.get("log_excerpt")
                    or compile_data.get("message")
                    or "Compilation failed"
                )
                logger.warning("Attempt %d compile failed: %s", attempt, current_error)
                continue

            video_path = compile_data.get("video_path")
            if not video_path:
                current_error = "Compile reported ok but no video_path returned."
                continue

            # 3. Video Validation
            print(f"-> VALIDATING_VIDEO Validating rendered animation (attempt {attempt})…", file=sys.stderr, flush=True)
            val_res = validate_video_file(video_path)
            if not val_res.ok:
                current_error = f"Video validation failed: {val_res.error}"
                logger.warning("Attempt %d video validation failed: %s", attempt, current_error)
                continue

            # SUCCESS! Promote artifacts to the main run_dir
            final_video = workspace / "final.mp4"
            final_scene = workspace / f"{scene_name}.py"
            shutil.copy2(video_path, final_video)
            final_scene.write_text(current_code, encoding="utf-8")

            # Update manifest
            manifest_path = workspace / "manifest.json"
            manifest = {}
            if manifest_path.is_file():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except Exception:
                    manifest = {}
            manifest["video_path"] = str(final_video.resolve())
            manifest["scene_file"] = f"{scene_name}.py"
            manifest["repaired"] = True
            manifest["repair_attempts"] = attempt
            manifest["last_compile"] = {
                "ok": True,
                "video_path": str(final_video.resolve()),
                "scene_name": scene_name,
            }
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            logger.info("Self-healing repair succeeded on attempt %d/%d", attempt, max_attempts)
            return RepairResult(
                ok=True,
                video_path=str(final_video.resolve()),
                scene_path=str(final_scene.resolve()),
                attempts_made=attempt,
                repaired_code=current_code,
            )

        except Exception as exc:
            current_error = f"Exception during repair attempt {attempt}: {exc}"
            logger.exception("Error during repair loop: %s", exc)

    logger.error("All %d repair attempts exhausted for run_dir %s", max_attempts, workspace)
    return RepairResult(
        ok=False,
        attempts_made=max_attempts,
        final_error=current_error,
        repaired_code=current_code,
    )
