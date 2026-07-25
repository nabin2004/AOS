from __future__ import annotations

from dbos_setup import DBOS

from tools.coder_workspace import (
    OutputDirError,
    load_manifest,
    resolve_output_dir,
    result_json,
)


@DBOS.step()
def manim_read(output_dir: str | None = None) -> str:
    try:
        workspace = resolve_output_dir(output_dir)
    except OutputDirError as e:
        return result_json(
            ok=False,
            step="read",
            output_dir=output_dir,
            error="invalid_output_dir",
            message=str(e),
        )

    manifest = load_manifest(workspace)

    scene_file = manifest.get("scene_file")
    if not scene_file:
        return result_json(
            ok=False,
            step="read",
            output_dir=str(workspace),
            error="No scene_file recorded in manifest.",
        )

    scene_path = workspace / scene_file
    if not scene_path.exists():
        return result_json(
            ok=False,
            step="read",
            output_dir=str(workspace),
            scene_file=scene_file,
            error="Scene file does not exist.",
        )

    code = scene_path.read_text(encoding="utf-8")

    return result_json(
        ok=True,
        step="read",
        output_dir=str(workspace),
        scene_file=scene_file,
        bytes=len(code.encode("utf-8")),
        code=code,
        message=f"Read Manim code from {scene_path}.",
    )
