from __future__ import annotations

from dbos_setup import DBOS

from tools.coder_workspace import (
    OutputDirError,
    load_manifest,
    record_step,
    resolve_output_dir,
    result_json,
    save_manifest,
    scene_file_path,
)
from tools.manim_source import prepare_manim_source
from ir.manim_ir import LectureIR
from tools.deps import ToolDeps

async def write_lecture_py_for_ir(lecture_ir: LectureIR, deps: ToolDeps) -> str:
    """Use coder agent to generate the python script for the given IR."""
    from coder_run import arrange_coder_artifacts
    from coder_agent import coder_agent
    from coder_prompt import build_coder_user_prompt, plan_to_payload
    from llm_config import is_ollama, model_for
    
    run_dir = deps.workspace_dir
    payload = plan_to_payload(lecture_ir.lecture)
    # Add scene plans so coder agent knows what scenes to generate
    payload["scenes"] = [s.model_dump(mode="json") for s in lecture_ir.scenes]
    
    local_coder = is_ollama(model_for("coder"))
    prompt = build_coder_user_prompt(
        topic=lecture_ir.lecture.title,
        subject=lecture_ir.lecture.subject,
        output_dir=run_dir,
        plan_payload=payload,
        compact=local_coder,
        include_codemode_hint=local_coder,
    )
    result = await coder_agent.run(prompt)
    
    # Try to extract codemode text
    summary = str(result.output)
    from tools.manim_source import extract_codemode_dump
    extracted = extract_codemode_dump(summary)
    
    code = extracted.code if extracted else summary
    # write it out
    scene_name = "lecture"
    scene_path = run_dir / f"{scene_name}.py"
    code = prepare_manim_source(code)
    scene_path.write_text(code, encoding="utf-8")
    return str(scene_path)


@DBOS.step()
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
        if not isinstance(code, str) or not code.strip():
            return result_json(
                ok=False,
                step="write",
                output_dir=output_dir,
                error="empty_code",
                message="Refusing to write: code is empty (would wipe the scene file).",
            )

        workspace = resolve_output_dir(output_dir)
        scene_path = scene_file_path(workspace, scene_name)
        code = prepare_manim_source(code)
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
    except OutputDirError as e:
        return result_json(
            ok=False,
            step="write",
            output_dir=output_dir,
            error="invalid_output_dir",
            message=str(e),
        )
    except Exception as e:
        return result_json(
            ok=False,
            step="write",
            output_dir=output_dir,
            error=str(e),
            message=f"Failed to write Manim code: {e}",
        )
