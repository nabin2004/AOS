"""
Metric 1: Executability (Pass@1)
==================================
Binary — does the generated code run without exceptions in Manim CE?

Checks:
  - Python syntax validity (ast.parse)
  - Import resolution (from manim import *)
  - Scene class presence
  - Manim rendering (subprocess with timeout)
"""

import ast
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


def check_syntax(code: str) -> dict[str, Any]:
    """
    Check if code is syntactically valid Python.

    Returns:
        {"valid": bool, "error": str | None, "error_line": int | None}
    """
    try:
        ast.parse(code)
        return {"valid": True, "error": None, "error_line": None}
    except SyntaxError as e:
        return {
            "valid": False,
            "error": str(e),
            "error_line": e.lineno,
        }


def check_scene_class(code: str) -> dict[str, Any]:
    """
    Check that code defines at least one Scene subclass.

    Returns:
        {"has_scene": bool, "scene_names": list[str], "scene_count": int}
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"has_scene": False, "scene_names": [], "scene_count": 0}

    scene_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = ""
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr

                if base_name in (
                    "Scene", "MovingCameraScene", "ThreeDScene",
                    "ZoomedScene", "VectorScene",
                ):
                    scene_names.append(node.name)

    return {
        "has_scene": len(scene_names) > 0,
        "scene_names": scene_names,
        "scene_count": len(scene_names),
    }


def check_imports(code: str) -> dict[str, Any]:
    """
    Validate that code uses Manim CE imports (not GL).

    Returns:
        {"has_manim_import": bool, "has_gl_import": bool, "imports": list[str]}
    """
    has_manim = bool(re.search(r"from\s+manim\s+import|import\s+manim", code))
    has_gl = bool(re.search(
        r"from\s+manim_imports_ext|from\s+manimlib|from\s+manim_gl|import\s+manimlib",
        code,
    ))

    imports = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
    except SyntaxError:
        pass

    return {
        "has_manim_import": has_manim,
        "has_gl_import": has_gl,
        "imports": imports,
    }


def run_manim_code(
    code: str,
    scene_name: str | None = None,
    timeout: int = 60,
    quality: str = "l",        # low quality for speed
) -> dict[str, Any]:
    """
    Execute Manim code in a subprocess and capture results.

    Args:
        code: Python source code
        scene_name: Scene class to render (auto-detected if None)
        timeout: Max seconds to wait
        quality: Manim quality flag (l=low, m=medium, h=high)

    Returns:
        {
            "success": bool,
            "returncode": int,
            "stdout": str,
            "stderr": str,
            "video_path": str | None,
            "error_type": str | None,      # ImportError, AttributeError, etc.
            "error_message": str | None,
            "command": list[str],
            "render_duration_s": float,
        }
    """
    # Auto-detect scene name if not provided
    if scene_name is None:
        info = check_scene_class(code)
        if info["scene_names"]:
            scene_name = info["scene_names"][0]
        else:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "No Scene subclass found in code",
                "video_path": None,
                "error_type": "NoSceneClass",
                "error_message": "No Scene subclass found in code",
                "command": [],
                "render_duration_s": 0.0,
            }

    with tempfile.TemporaryDirectory(prefix="manibench_") as tmpdir:
        # Write code to file
        code_path = Path(tmpdir) / "scene.py"
        code_path.write_text(code, encoding="utf-8")

        # Build manim command
        cmd = [
            sys.executable, "-m", "manim", f"-q{quality}",
            "--disable_caching",
            "--media_dir", str(Path(tmpdir) / "media"),
            str(code_path),
            scene_name,
        ]

        t0 = time.monotonic()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir,
            )
            duration = round(time.monotonic() - t0, 3)

            # Check for video output
            video_path = None
            media_dir = Path(tmpdir) / "media" / "videos" / "scene"
            if media_dir.exists():
                videos = list(media_dir.rglob("*.mp4"))
                if videos:
                    video_path = str(videos[0])

            # Parse error type from stderr
            error_type = None
            error_message = None
            if result.returncode != 0:
                error_type, error_message = _parse_error(result.stderr)

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": (result.stdout or "")[-2000:],
                "stderr": (result.stderr or "")[-2000:],
                "video_path": video_path,
                "error_type": error_type,
                "error_message": error_message,
                "command": cmd,
                "render_duration_s": duration,
            }

        except subprocess.TimeoutExpired as e:
            duration = round(time.monotonic() - t0, 3)
            stdout = (e.stdout or "")[-2000:] if isinstance(e.stdout, str) else ""
            stderr = (e.stderr or "")[-2000:] if isinstance(e.stderr, str) else ""
            timeout_msg = f"Timeout after {timeout}s"
            return {
                "success": False,
                "returncode": -1,
                "stdout": stdout,
                "stderr": (stderr + "\n" + timeout_msg).strip(),
                "video_path": None,
                "error_type": "Timeout",
                "error_message": f"Rendering exceeded {timeout}s time limit",
                "command": cmd,
                "render_duration_s": duration,
            }
        except FileNotFoundError as e:
            duration = round(time.monotonic() - t0, 3)
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "video_path": None,
                "error_type": "FileNotFoundError",
                "error_message": str(e)[:200],
                "command": cmd,
                "render_duration_s": duration,
            }


def _parse_error(stderr: str) -> tuple[str | None, str | None]:
    """Extract error type and message from stderr."""
    # Look for common Python exception patterns
    patterns = [
        (r"(ImportError|ModuleNotFoundError):\s*(.+)", "ImportError"),
        (r"(AttributeError):\s*(.+)", "AttributeError"),
        (r"(TypeError):\s*(.+)", "TypeError"),
        (r"(ValueError):\s*(.+)", "ValueError"),
        (r"(NameError):\s*(.+)", "NameError"),
        (r"(RuntimeError):\s*(.+)", "RuntimeError"),
        (r"(KeyError):\s*(.+)", "KeyError"),
        (r"(IndexError):\s*(.+)", "IndexError"),
        (r"(FileNotFoundError):\s*(.+)", "FileNotFoundError"),
        (r"(Exception):\s*(.+)", "Exception"),
    ]
    for pattern, etype in patterns:
        match = re.search(pattern, stderr)
        if match:
            return etype, match.group(0).strip()[:200]

    if stderr.strip():
        return "UnknownError", stderr.strip()[-200:]
    return None, None


def compute_executability(code: str, timeout: int = 60, skip_render: bool = False) -> dict[str, Any]:
    """
    Full executability check pipeline.

    Args:
        code: The generated Python/Manim code to check.
        timeout: Seconds to allow for Manim rendering.
        skip_render: If True, skip actual Manim execution (static analysis only).

    Returns:
        {
            "executability": 1 or 0,
            "syntax_valid": bool,
            "has_scene": bool,
            "has_manim_import": bool,
            "has_gl_import": bool,
            "render_success": bool,
            "error_type": str | None,
            "error_message": str | None,
            "scene_names": list[str],
            "render_attempted": bool,
            "render_duration_s": float,
            "returncode": int | None,
            "stdout": str,
            "stderr": str,
            "command": list[str],
        }
    """
    result = {
        "executability": 0,
        "syntax_valid": False,
        "has_scene": False,
        "has_manim_import": False,
        "has_gl_import": False,
        "render_success": False,
        "render_attempted": False,
        "render_duration_s": 0.0,
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "command": [],
        "error_type": None,
        "error_message": None,
        "scene_names": [],
    }

    # Step 1: Syntax check
    syntax = check_syntax(code)
    result["syntax_valid"] = syntax["valid"]
    if not syntax["valid"]:
        result["error_type"] = "SyntaxError"
        result["error_message"] = syntax["error"]
        return result

    # Step 2: Import check
    imports = check_imports(code)
    result["has_manim_import"] = imports["has_manim_import"]
    result["has_gl_import"] = imports["has_gl_import"]

    # Step 3: Scene class check
    scene = check_scene_class(code)
    result["has_scene"] = scene["has_scene"]
    result["scene_names"] = scene["scene_names"]
    if not scene["has_scene"]:
        result["error_type"] = "NoSceneClass"
        result["error_message"] = "No Scene subclass found"
        return result

    # Step 4: Execution (skip if requested)
    if skip_render:
        # Static analysis passed — count as executable
        result["render_success"] = True
        result["executability"] = 1
        result["render_attempted"] = False
        return result

    render = run_manim_code(code, timeout=timeout)
    result["render_attempted"] = True
    result["render_success"] = render["success"]
    result["error_type"] = render["error_type"]
    result["error_message"] = render["error_message"]
    result["render_duration_s"] = render.get("render_duration_s", 0.0)
    result["returncode"] = render.get("returncode")
    result["stdout"] = render.get("stdout", "")
    result["stderr"] = render.get("stderr", "")
    result["command"] = render.get("command", [])

    # Final verdict
    result["executability"] = 1 if render["success"] else 0
    return result
