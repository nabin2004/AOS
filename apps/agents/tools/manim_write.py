from __future__ import annotations

from tools.coder_workspace import (
    load_manifest,
    record_step,
    resolve_output_dir,
    result_json,
    save_manifest,
    scene_file_path,
)


def manim_write(
    code: str,
    scene_name: str = "scene",
    output_dir: str | None = None,
) -> str:
    """
    Write Manim code into the coder workspace directory.

    Layout (all paths relative to output_dir, default workspace/coder):
      - scene.py          — Manim source (name from scene_name)
      - manifest.json     — structured run state
      - logs/             — compile logs (written by compile_manim_code)

    Returns a JSON summary with paths and status.
    """
    try:
        workspace = resolve_output_dir(output_dir)
        scene_path = scene_file_path(workspace, scene_name)
        scene_path.write_text(code, encoding="utf-8")

        manifest = load_manifest(workspace)
        manifest["output_dir"] = str(workspace)
        manifest["scene_file"] = str(scene_path.relative_to(workspace))
        manifest["last_write"] = {
            "ok": True,
            "scene_name": scene_name,
            "bytes": len(code.encode("utf-8")),
        }
        save_manifest(workspace, manifest)
        record_step(
            workspace,
            "write",
            {
                "ok": True,
                "scene_file": manifest["scene_file"],
            },
        )

        return result_json(
            ok=True,
            step="write",
            output_dir=str(workspace),
            scene_file=manifest["scene_file"],
            manifest=str(workspace / "manifest.json"),
            message=f"Wrote Manim code to {scene_path}.",
        )
    except Exception as e:
        return result_json(
            ok=False,
            step="write",
            output_dir=output_dir,
            error=str(e),
            message=f"Failed to write Manim code: {e}",
        )
