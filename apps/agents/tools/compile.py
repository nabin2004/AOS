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
from tools.manim_source import has_set_speech_service, prepare_manim_source
from tools.voiceover_quality import FILLER_HINT, FILLER_VOICEOVER, filler_voiceover_error
from ir.manim_ir import LectureIR

def persist_lecture_ir(workspace_dir: Path, lecture_ir: LectureIR) -> Path:
    """Write the IR json to the workspace."""
    out = workspace_dir / "lecture_ir.json"
    out.write_text(lecture_ir.model_dump_json(indent=2), encoding="utf-8")
    return out

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

_VOICEOVER_HINT = (
    "Animate scenes must subclass VoiceoverScene, call "
    "set_speech_service(AOSSpeechService(...)) before the first voiceover, "
    "and wrap teaching beats in with self.voiceover(text=...) as tracker:. "
    "Silent Scene / self.play without voiceover is not allowed. "
    + FILLER_HINT
)

_AUDIO_HINT = (
    "Rendered MP4 has no audio stream. Install SoX (manim-voiceover needs it), "
    "confirm AOSSpeechService/Pocket TTS works, and ensure voiceover(...) runs "
    "during construct()."
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


def _bases_include_voiceover(node: ast.ClassDef) -> bool:
    for base in node.bases:
        name = _base_name(base)
        if name in ("VoiceoverScene", "VoiceoverSlideScene"):
            return True
    return False


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _has_voiceover_call(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and _call_name(child) == "voiceover":
            return True
        if isinstance(child, ast.With):
            for item in child.items:
                ctx = item.context_expr
                if isinstance(ctx, ast.Call) and _call_name(ctx) == "voiceover":
                    return True
    return False


def validate_voiceover_scene(code: str) -> str | None:
    """Return an error code if source is missing VoiceoverScene + voiceover()."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"syntax_error:{exc.msg}"

    voiceover_classes: list[ast.ClassDef] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and _bases_include_voiceover(node):
            voiceover_classes.append(node)

    if not voiceover_classes:
        return "missing_voiceover_scene"

    if not any(_has_voiceover_call(cls) for cls in voiceover_classes):
        return "missing_voiceover_calls"
    if not any(has_set_speech_service(cls) for cls in voiceover_classes):
        return "missing_speech_service"
    filler = filler_voiceover_error(code)
    if filler is not None:
        return filler
    return None


def _find_scene_mp4(workspace: Path, scene_class: str) -> Path | None:
    """Prefer the final scene MP4 under media/, skipping partial_movie_files."""
    media = workspace / "media"
    if not media.is_dir():
        return None

    preferred: list[Path] = []
    fallback: list[Path] = []
    for path in media.rglob("*.mp4"):
        if not path.is_file():
            continue
        if "partial_movie_files" in path.parts:
            continue
        if path.stem == scene_class:
            preferred.append(path)
        else:
            fallback.append(path)

    pool = preferred or fallback
    if not pool:
        return None
    return max(pool, key=lambda p: p.stat().st_size)


def mp4_has_audio_stream(mp4_path: Path) -> bool | None:
    """Return True/False if ffprobe can tell; None if ffprobe is unavailable."""
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "csv=p=0",
                str(mp4_path),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except FileNotFoundError:
        return None
    except (OSError, subprocess.TimeoutExpired):
        return None

    if proc.returncode != 0:
        return False
    return any(line.strip() == "audio" for line in proc.stdout.splitlines())


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
        code = prepare_manim_source(code)
        fallback_class = _scene_class_name(scene_name)
        scene_class = _discover_scene_class(code, fallback_class)
        scene_path.write_text(code, encoding="utf-8")

        voiceover_error = validate_voiceover_scene(code)
        if voiceover_error is not None:
            manifest = load_manifest(workspace)
            manifest["output_dir"] = str(workspace)
            manifest["scene_file"] = str(scene_path.relative_to(workspace))
            manifest["last_compile"] = {
                "ok": False,
                "returncode": None,
                "scene_name": scene_name,
                "scene_class": scene_class,
                "failure_marker": voiceover_error,
                "tex_failure": False,
            }
            save_manifest(workspace, manifest)
            record_step(
                workspace,
                "compile",
                {
                    "ok": False,
                    "scene_file": manifest["scene_file"],
                    "failure_marker": voiceover_error,
                    "scene_class": scene_class,
                },
            )
            hint = FILLER_HINT if voiceover_error == FILLER_VOICEOVER else _VOICEOVER_HINT
            return result_json(
                ok=False,
                step="compile",
                output_dir=str(workspace),
                scene_file=manifest["scene_file"],
                scene_class=scene_class,
                error=voiceover_error,
                failure_marker=voiceover_error,
                message=f"Compilation refused: {hint}",
            )

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
        video_path: str | None = None
        has_audio: bool | None = None

        if ok:
            mp4 = _find_scene_mp4(workspace, scene_class)
            if mp4 is not None:
                video_path = str(mp4.resolve())
                has_audio = mp4_has_audio_stream(mp4)
                if has_audio is False:
                    ok = False
                    failure_marker = "no_audio_stream"
                    # Surface SoX / voiceover hints that often appear in manim logs.
                    if "sox" in output.lower() and "not found" in output.lower():
                        failure_marker = "no_audio_stream_sox_missing"

        if ok:
            message = "Compilation successful."
        elif failure_marker in ("no_audio_stream", "no_audio_stream_sox_missing"):
            message = f"Compilation failed: {_AUDIO_HINT}"
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
        if video_path:
            manifest["video_path"] = video_path
        manifest["last_compile"] = {
            "ok": ok,
            "returncode": proc.returncode,
            "scene_name": scene_name,
            "scene_class": scene_class,
            "failure_marker": failure_marker,
            "tex_failure": tex_failure,
            "video_path": video_path,
            "has_audio": has_audio,
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
                "video_path": video_path,
                "has_audio": has_audio,
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
            video_path=video_path,
            has_audio=has_audio,
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
