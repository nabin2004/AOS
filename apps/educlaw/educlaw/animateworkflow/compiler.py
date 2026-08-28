from __future__ import annotations

import subprocess
from pathlib import Path

from .contracts import CompileError, CompileResult, FailureCategory, FinalCode
from .validator import validate_generated_code
from educlaw.sandbox import DockerSandbox


def compile_final_code(
    final_code: FinalCode,
    *,
    cwd: Path,
    quality: str = "l",
    timeout: int = 180,
) -> CompileResult:
    """Render generated Manim code in the existing Docker sandbox."""
    validation_errors = validate_generated_code(final_code)
    if validation_errors:
        return CompileResult(success=False, errors=validation_errors)

    source_dir = cwd / ".educlaw" / "animateworkflow"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_file = source_dir / "generated_scene.py"
    source_file.write_text(final_code.code, encoding="utf-8")

    sandbox = DockerSandbox(cwd, quality=quality)
    try:
        process = sandbox.run(
            sandbox.manim_argv(source_file.relative_to(cwd).as_posix(), final_code.scene_name),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return CompileResult(
            success=False,
            errors=[
                CompileError(
                    category=FailureCategory.RENDER_TIMEOUT,
                    message=f"Manim render exceeded the {timeout}s timeout",
                )
            ],
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        return CompileResult(
            success=False,
            errors=[
                CompileError(
                    category=FailureCategory.ENVIRONMENT_ERROR,
                    message=f"Docker is unavailable or could not start the Manim sandbox: {exc}",
                )
            ],
        )

    if process.returncode != 0:
        category = _classify_process_error(sandbox.format_result(process))
        return CompileResult(
            success=False,
            errors=[
                CompileError(
                    category=category,
                    message=sandbox.format_result(process),
                )
            ],
        )

    videos = sorted(cwd.glob("media/**/*.mp4"))
    if not videos:
        return CompileResult(
            success=False,
            errors=[
                CompileError(
                    category=FailureCategory.RENDER_TIMEOUT,
                    message="Manim exited successfully but produced no MP4 output",
                )
            ],
        )
    return CompileResult(success=True, output_path=str(videos[-1]))


def _classify_process_error(message: str) -> FailureCategory:
    text = message.lower()
    if any(pattern in text for pattern in ("docker daemon", "dockerdesktoplinuxengine", "pipe/not found", "connection refused")):
        return FailureCategory.ENVIRONMENT_ERROR
    if "syntaxerror" in text:
        return FailureCategory.SYNTAX_ERROR
    if "modulenotfounderror" in text or "importerror" in text:
        return FailureCategory.MISSING_IMPORTS
    if "latex" in text or "texerror" in text:
        return FailureCategory.LATEX_ERROR
    if any(pattern in text for pattern in ("point array", "point dimension", "shape mismatch", "malformed point")):
        return FailureCategory.MALFORMED_POINT_ARRAYS
    if "unexpected keyword argument" in text or "invalid keyword" in text:
        return FailureCategory.HALLUCINATED_KWARGS
    return FailureCategory.RENDER_ERROR
