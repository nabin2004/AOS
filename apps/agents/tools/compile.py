from __future__ import annotations

import subprocess

from tools.coder_workspace import (
    load_manifest,
    record_step,
    resolve_output_dir,
    result_json,
    save_manifest,
    scene_file_path,
)


def compile_manim_code(
    code: str,
    scene_name: str = "scene",
    output_dir: str | None = None,
) -> str:
    """
    Compile Manim code inside the coder workspace directory.

    Writes source to output_dir/scene.py (or scene_name.py), runs `manim -pqh`
    with cwd=output_dir so media stays under that folder, and saves logs to
    output_dir/logs/compile.log.

    Returns a JSON summary with compile status, paths, and log excerpt.
    """
    try:
        workspace = resolve_output_dir(output_dir)
        scene_path = scene_file_path(workspace, scene_name)
        scene_path.write_text(code, encoding="utf-8")

        log_path = workspace / "logs" / "compile.log"
        cmd = ["uv", "run", "manim", "-pqh", scene_path.name]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=workspace,
        )
        output = proc.stdout + proc.stderr
        log_path.write_text(output, encoding="utf-8")

        ok = proc.returncode == 0
        manifest = load_manifest(workspace)
        manifest["output_dir"] = str(workspace)
        manifest["scene_file"] = str(scene_path.relative_to(workspace))
        manifest["compile_log"] = str(log_path.relative_to(workspace))
        manifest["last_compile"] = {
            "ok": ok,
            "returncode": proc.returncode,
            "scene_name": scene_name,
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
            },
        )

        return result_json(
            ok=ok,
            step="compile",
            output_dir=str(workspace),
            scene_file=manifest["scene_file"],
            compile_log=manifest["compile_log"],
            manifest=str(workspace / "manifest.json"),
            returncode=proc.returncode,
            log_excerpt=output[-4000:] if len(output) > 4000 else output,
            message=(
                "Compilation successful."
                if ok
                else f"Compilation failed with return code {proc.returncode}."
            ),
        )
    except Exception as e:
        return result_json(
            ok=False,
            step="compile",
            output_dir=output_dir,
            error=str(e),
            message=f"Unexpected compile error: {e}",
        )
