"""Run compile → render → mux on an existing workspace (no agent graph)."""

from __future__ import annotations

import sys
from pathlib import Path

from ir.manim_ir import LectureIR
from tools.deps import ToolDeps
from tools.pipeline import run_full_pipeline
from tools.render import summarize_render_results

DEFAULT_WORKSPACE = Path("runs") / "final_final_graph"


def main(workspace: Path = DEFAULT_WORKSPACE) -> None:
    ir_path = workspace / "lecture_ir.json"
    if not ir_path.exists():
        print(f"Missing {ir_path}. Run the agent pipeline first or pass a workspace with lecture_ir.json.")
        sys.exit(1)

    lecture_ir = LectureIR.model_validate_json(ir_path.read_text(encoding="utf-8"))
    deps = ToolDeps(workspace_dir=workspace)
    result = run_full_pipeline(lecture_ir, deps)

    print(f"Lecture IR: {result.lecture_ir_path}")
    if result.lecture_py_path:
        print(f"Manim:      {result.lecture_py_path}")
    print(f"Narration:  {len(result.narration)} clip(s)")
    render_summary = summarize_render_results(result.render_results)
    print(
        f"Rendered:   {render_summary['succeeded']}/{render_summary['attempted']} succeeded"
    )
    if render_summary["failures"]:
        print("Render failures:")
        for scene_class, snippet in render_summary["failures"]:
            print(f"  {scene_class}: {snippet}")
    print(f"Muxed:      {len(result.scene_videos)} scene(s)")
    if result.skipped_scenes:
        print(f"Skipped:    {', '.join(result.skipped_scenes)}")
    if result.final_video_path:
        print(f"Final video: {result.final_video_path}")
    else:
        print("Final video: not produced (check Docker, ffmpeg, and render_results.json)")
    print(f"Pipeline summary: {workspace / 'pipeline_result.json'}")


if __name__ == "__main__":
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_WORKSPACE
    main(ws)
