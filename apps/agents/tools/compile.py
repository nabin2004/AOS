from __future__ import annotations

import ast
import os
import re
import subprocess
from pathlib import Path
from dbos_setup import DBOS
from error_feedback import summarize_diagnostic_output

from tools.coder_workspace import (
    OutputDirError,
    load_manifest,
    record_step,
    resolve_output_dir,
    result_json,
    save_manifest,
    scene_file_path,
)

_FAILURE_MARKERS = (
    "There are no scenes inside that module",
    "Error while rendering",
    "standalone.cls",
    "LaTeX Error",
    "is not in the script",
)

_SCENE_BASE_NAMES = frozenset(
    {
        "Scene",
        "VoiceoverScene",
        "ThreeDScene",
        "MovingCameraScene",
        "ZoomedScene",
        "VectorScene",
        "LinearTransformationScene",
    }
)

_TEX_HINT = (
    "LaTeX/TeX environment issue (e.g. missing standalone.cls). "
    "Install texlive-latexextra texlive-fontsrecommended texlive-mathscience "
    "(Arch) or texlive-latex-extra texlive-fonts-recommended texlive-science "
    "(Debian). Do not thrash on string escaping — fix TeX or fall back to Text once."
)


def _scene_class_name(scene_name: str) -> str:
    name = (scene_name or "scene").strip()
    if name.endswith(".py"):
        name = name[: -len(".py")]
    return name or "scene"


def _base_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_scene_class(node: ast.ClassDef) -> bool:
    for base in node.bases:
        name = _base_name(base)
        if name in _SCENE_BASE_NAMES or (name is not None and name.endswith("Scene")):
            return True
    return False


def _discover_scene_class(code: str, fallback: str) -> str:
    """Prefer the first Scene subclass in source over the filename stem."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return fallback

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and _is_scene_class(node):
            return node.name
    return fallback


def _output_indicates_failure(output: str) -> str | None:
    for marker in _FAILURE_MARKERS:
        if marker in output:
            return marker
    # Manim: "Foo is not in the script" when class name mismatches.
    if re.search(r"\bis not in the script\b", output):
        return "is not in the script"
    return None


def _is_tex_failure(marker: str | None, output: str) -> bool:
    if marker in ("standalone.cls", "LaTeX Error"):
        return True
    return "LaTeX Error" in output or "standalone.cls" in output


def _manim_env() -> dict[str, str]:
    """Ensure user TEXMFHOME (~/texmf) is visible to Manim's pdflatex."""
    env = os.environ.copy()
    texmf = Path.home() / "texmf"
    if texmf.is_dir():
        env.setdefault("TEXMFHOME", str(texmf))
    return env


def _manim_quality_flag() -> str:
    """Manim -q flag letter: l|m|h|k. Default low for fast agent iteration."""
    raw = os.getenv("AOS_MANIM_QUALITY", "l").strip().lower()
    if raw.startswith("-q") and len(raw) >= 3:
        raw = raw[2:]
    if raw in ("l", "m", "h", "k", "low", "medium", "high", "fourk", "4k"):
        return {
            "l": "l",
            "low": "l",
            "m": "m",
            "medium": "m",
            "h": "h",
            "high": "h",
            "k": "k",
            "fourk": "k",
            "4k": "k",
        }[raw]
    return "l"


@DBOS.step()
def compile_manim_code(
    code: str,
    scene_name: str = "scene",
    output_dir: str | None = None,
) -> str:
    """
    Compile Manim code inside the coder workspace directory.

    Writes source to output_dir/{scene_name}.py, runs `manim -q<quality> <file> <SceneClass>`
    with cwd=output_dir so media stays under that folder, and saves logs to
    output_dir/logs/compile.log.

    Quality defaults to `-ql` (fast iteration). Override with env AOS_MANIM_QUALITY=l|m|h|k.
    SFT traces use scene source + tool calls, not render pixels.

    Scene class is taken from the first Scene/VoiceoverScene subclass in the
    source when present; otherwise falls back to the scene_name stem.

    Returns a JSON summary with compile status, paths, and log excerpt.
    """
    try:
        if not isinstance(code, str) or not code.strip():
            return result_json(
                ok=False,
                step="compile",
                output_dir=output_dir,
                error="empty_code",
                message="Refusing to compile: code is empty (would wipe the scene file).",
            )

        workspace = resolve_output_dir(output_dir)
        scene_path = scene_file_path(workspace, scene_name)
        fallback_class = _scene_class_name(scene_name)
        scene_class = _discover_scene_class(code, fallback_class)
        scene_path.write_text(code, encoding="utf-8")

        log_path = workspace / "logs" / "compile.log"
        quality = _manim_quality_flag()
        cmd = ["uv", "run", "manim", f"-q{quality}", scene_path.name, scene_class]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=workspace,
            env=_manim_env(),
        )
        output = proc.stdout + proc.stderr
        log_path.write_text(output, encoding="utf-8")

        failure_marker = _output_indicates_failure(output)
        ok = proc.returncode == 0 and failure_marker is None
        tex_failure = _is_tex_failure(failure_marker, output)

        if ok:
            message = "Compilation successful."
        elif tex_failure:
            message = f"Compilation failed: {_TEX_HINT}"
        elif failure_marker and proc.returncode == 0:
            message = f"Compilation failed: {failure_marker}."
        elif failure_marker:
            message = f"Compilation failed ({failure_marker}) with return code {proc.returncode}."
        else:
            message = f"Compilation failed with return code {proc.returncode}."

        manifest = load_manifest(workspace)
        manifest["output_dir"] = str(workspace)
        manifest["scene_file"] = str(scene_path.relative_to(workspace))
        manifest["compile_log"] = str(log_path.relative_to(workspace))
        manifest["last_compile"] = {
            "ok": ok,
            "returncode": proc.returncode,
            "scene_name": scene_name,
            "scene_class": scene_class,
            "failure_marker": failure_marker,
            "tex_failure": tex_failure,
        }
        save_manifest(workspace, manifest)
        record_step(
            workspace,
            "compile",
            {
                "ok": ok,
                "returncode": proc.returncode,
                "scene_file": manifest["scene_file"],
                "compile_log": manifest["compile_log"],
                "failure_marker": failure_marker,
                "scene_class": scene_class,
                "tex_failure": tex_failure,
            },
        )

        return result_json(
            ok=ok,
            step="compile",
            output_dir=str(workspace),
            scene_file=manifest["scene_file"],
            scene_class=scene_class,
            compile_log=manifest["compile_log"],
            manifest=str(workspace / "manifest.json"),
            returncode=proc.returncode,
            failure_marker=failure_marker,
            tex_failure=tex_failure,
            log_excerpt=summarize_diagnostic_output(output, max_chars=1200),
            message=message,
        )
    except OutputDirError as e:
        return result_json(
            ok=False,
            step="compile",
            output_dir=output_dir,
            error="invalid_output_dir",
            message=str(e),
        )
    except Exception as e:
        return result_json(
            ok=False,
            step="compile",
            output_dir=output_dir,
            error=str(e),
            message=f"Unexpected compile error: {e}",
        )
