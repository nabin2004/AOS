"""Sandbox, render, and LSP tools registered on the EduClaw agent."""

from __future__ import annotations

import subprocess
from pathlib import Path
from pydantic_ai import Agent, RunContext

from educlaw.agent.deps import AgentDeps
from educlaw.animateworkflow.manim_kb import lookup_manim_symbol, search_manim_symbols
from educlaw.animateworkflow.visual_qc import inspect_video_frames
from educlaw.permissions.gate import PermissionAction, classify_command
from educlaw.sandbox.docker import PathJailError


def _emit(ctx: RunContext[AgentDeps], event: str, payload: object) -> None:
    if ctx.deps.emit:
        ctx.deps.emit(event, payload)


def register_tools(agent: Agent[AgentDeps, str]) -> None:
    @agent.tool
    async def sandbox_read(ctx: RunContext[AgentDeps], path: str) -> str:
        """Read a file inside the workspace. Path must stay under the project root."""
        action = PermissionAction(kind="read", summary=f"read {path}")
        if not await ctx.deps.gate.approve(action, emit=ctx.deps.emit):
            return "permission denied: read"
        try:
            host = ctx.deps.sandbox.jail(path)
        except PathJailError as exc:
            return f"path rejected: {exc}"
        if not host.is_file():
            return f"not a file: {path}"
        text = host.read_text(encoding="utf-8")
        if len(text) > 8000:
            text = text[:8000] + "\n…[truncated]"
        _emit(ctx, "tool", {"name": "sandbox_read", "path": path})
        return text

    @agent.tool
    async def sandbox_write(ctx: RunContext[AgentDeps], path: str, content: str) -> str:
        """Write a file inside the workspace, then run syntax/ty diagnostics on .py files."""
        action = PermissionAction(kind="write", summary=f"write {path}")
        if not await ctx.deps.gate.approve(action, emit=ctx.deps.emit):
            return "permission denied: write"
        try:
            host = ctx.deps.sandbox.jail(path)
        except PathJailError as exc:
            return f"path rejected: {exc}"
        host.parent.mkdir(parents=True, exist_ok=True)
        host.write_text(content, encoding="utf-8")
        report = ctx.deps.lsp.after_write(host)
        _emit(ctx, "tool", {"name": "sandbox_write", "path": path})
        extra = f"\n{report}" if report else ""
        return f"wrote {path} ({len(content)} bytes){extra}"

    @agent.tool
    async def sandbox_bash(ctx: RunContext[AgentDeps], command: str) -> str:
        """Run a bash command inside the manimcommunity/manim Docker container. Never on the host."""
        kind = classify_command(command)
        action = PermissionAction(kind=kind, summary=f"bash: {command}", detail=command)
        if not await ctx.deps.gate.approve(action, emit=ctx.deps.emit):
            return "permission denied: bash"
        argv = ctx.deps.sandbox.bash_argv(command)
        _emit(ctx, "tool", {"name": "sandbox_bash", "argv": argv})
        try:
            proc = ctx.deps.sandbox.run(argv)
        except FileNotFoundError as exc:
            return str(exc)
        return ctx.deps.sandbox.format_result(proc)

    @agent.tool
    async def manim_render(
        ctx: RunContext[AgentDeps],
        scene_file: str,
        scene_name: str,
        quality: str = "m",
    ) -> str:
        """Render a Manim scene in Docker (manimcommunity/manim). quality is l, m, h, or k."""
        action = PermissionAction(
            kind="render",
            summary=f"render {scene_file}::{scene_name} -q{quality}",
        )
        if not await ctx.deps.gate.approve(action, emit=ctx.deps.emit):
            return "permission denied: render"
        try:
            argv = ctx.deps.sandbox.manim_argv(scene_file, scene_name, quality)
        except PathJailError as exc:
            return f"path rejected: {exc}"
        _emit(ctx, "tool", {"name": "manim_render", "argv": argv})
        try:
            proc = ctx.deps.sandbox.run(argv, timeout=300)
        except FileNotFoundError as exc:
            return str(exc)
        return ctx.deps.sandbox.format_result(proc)

    @agent.tool
    async def test_render_manim(
        ctx: RunContext[AgentDeps],
        scene_name: str,
        scene_file: str = "scene.py",
        code: str = "",
    ) -> str:
        """Fast keyframe render probe (-ql -s) in sandbox to verify syntax, LaTeX, and visual layout before full render."""
        if code.strip():
            action = PermissionAction(kind="write", summary=f"write {scene_file}")
            if not await ctx.deps.gate.approve(action, emit=ctx.deps.emit):
                return "permission denied: write before test_render"
            try:
                host = ctx.deps.sandbox.jail(scene_file)
                host.parent.mkdir(parents=True, exist_ok=True)
                host.write_text(code, encoding="utf-8")
                report = ctx.deps.lsp.after_write(host)
                if report and "SyntaxError" in report:
                    return f"LSP Preflight Syntax Failure:\n{report}"
            except PathJailError as exc:
                return f"path rejected: {exc}"

        action = PermissionAction(
            kind="render",
            summary=f"keyframe render {scene_file}::{scene_name} -ql -s",
        )
        if not await ctx.deps.gate.approve(action, emit=ctx.deps.emit):
            return "permission denied: test_render"

        cmd = f"manim -ql -s --media_dir ./output {scene_file} {scene_name}"
        argv = ctx.deps.sandbox.bash_argv(cmd)
        _emit(ctx, "tool", {"name": "test_render_manim", "cmd": cmd})
        try:
            proc = ctx.deps.sandbox.run(argv, timeout=60)
        except FileNotFoundError as exc:
            return str(exc)

        output = ctx.deps.sandbox.format_result(proc)
        if proc.returncode != 0:
            return f"Keyframe Probe Failed (exit code {proc.returncode}). Stderr trace:\n{output[-1500:]}"

        keyframe_path = f"output/images/{Path(scene_file).stem}/{scene_name}.png"
        return f"Keyframe Probe PASSED (exit code 0).\nKeyframe image generated: {keyframe_path}\nReady for full scene rendering via manim_render."

    @agent.tool

    async def syntax_check(ctx: RunContext[AgentDeps], path: str) -> str:
        """Parse a Python file with ast. Cheap syntax feedback after edits."""
        try:
            host = ctx.deps.sandbox.jail(path)
        except PathJailError as exc:
            return f"path rejected: {exc}"
        if not host.is_file():
            return f"not a file: {path}"
        return ctx.deps.lsp.syntax_check(host)

    @agent.tool
    async def lsp_diagnostics(ctx: RunContext[AgentDeps], path: str) -> str:
        """Run ast.parse and `ty check` on a file when ty is installed."""
        try:
            host = ctx.deps.sandbox.jail(path)
        except PathJailError as exc:
            return f"path rejected: {exc}"
        if not host.is_file():
            return f"not a file: {path}"
        return ctx.deps.lsp.diagnostics(host)

    @agent.tool
    async def lsp_definition(ctx: RunContext[AgentDeps], symbol: str, path: str = "") -> str:
        """Find the definition, line number, signature, and docstring of a Python symbol (class/func)."""
        target_path = None
        if path.strip():
            try:
                target_path = ctx.deps.sandbox.jail(path)
            except PathJailError as exc:
                return f"path rejected: {exc}"
        _emit(ctx, "tool", {"name": "lsp_definition", "symbol": symbol, "path": path})
        return ctx.deps.lsp.find_definition(symbol, target_path=target_path)

    @agent.tool
    async def lsp_symbols(ctx: RunContext[AgentDeps], path: str = "", query: str = "") -> str:
        """List symbols in a specific file or search Python symbols across the workspace."""
        if path.strip():
            try:
                host = ctx.deps.sandbox.jail(path)
            except PathJailError as exc:
                return f"path rejected: {exc}"
            _emit(ctx, "tool", {"name": "lsp_symbols", "path": path})
            return ctx.deps.lsp.file_symbols(host)

        _emit(ctx, "tool", {"name": "lsp_symbols", "query": query})
        return ctx.deps.lsp.workspace_symbols(query=query)

    @agent.tool
    async def manim_api_lookup(ctx: RunContext[AgentDeps], symbol_name: str) -> str:
        """Lookup valid Manim Community classes, animations, transforms, and keyword arguments."""
        doc = lookup_manim_symbol(symbol_name)
        _emit(ctx, "tool", {"name": "manim_api_lookup", "symbol": symbol_name})
        if not doc:
            matches = search_manim_symbols(symbol_name)
            if not matches:
                return f"No Manim symbol found matching '{symbol_name}'."
            suggestions = ", ".join(m.name for m in matches)
            return f"Symbol '{symbol_name}' not found. Did you mean: {suggestions}?"

        lines = [
            f"Symbol: {doc.name} ({doc.symbol_type})",
            f"Signature: {doc.signature}",
            f"Description: {doc.description}",
        ]
        if doc.valid_kwargs:
            lines.append(f"Supported kwargs: {', '.join(doc.valid_kwargs)}")
        if doc.common_pitfalls:
            lines.append("Pitfalls / Anti-patterns:")
            for p in doc.common_pitfalls:
                lines.append(f"  - {p}")
        if doc.example_usage:
            lines.append(f"Example:\n{doc.example_usage}")
        return "\n".join(lines)

    @agent.tool
    async def manim_concat_scenes(
        ctx: RunContext[AgentDeps],
        scene_videos: list[str],
        output_path: str = "final_lecture.mp4",
    ) -> str:
        """Stitch multiple scene video files into a single cohesive lecture MP4 via ffmpeg."""
        action = PermissionAction(kind="bash", summary=f"concat {len(scene_videos)} videos -> {output_path}")
        if not await ctx.deps.gate.approve(action, emit=ctx.deps.emit):
            return "permission denied: concat"

        try:
            out_host = ctx.deps.sandbox.jail(output_path)
            in_hosts = [ctx.deps.sandbox.jail(p) for p in scene_videos]
        except PathJailError as exc:
            return f"path rejected: {exc}"

        success, result, msg = concat_scene_videos(in_hosts, out_host)
        _emit(ctx, "tool", {"name": "manim_concat_scenes", "success": success, "output": str(result)})
        if success:
            return f"Successfully concatenated {len(in_hosts)} scenes into {out_host.as_posix()}."
        return f"Warning: Concatenation failed ({msg}). Retaining individual scene videos: {[p.as_posix() for p in in_hosts]}."

    @agent.tool
    async def visual_qc_check(ctx: RunContext[AgentDeps], video_path: str) -> str:
        """Inspect a rendered Manim MP4 video for visual collisions, off-screen clipping, and contrast issues."""
        try:
            host_video = ctx.deps.sandbox.jail(video_path)
        except PathJailError as exc:
            return f"path rejected: {exc}"

        if not host_video.is_file():
            return f"video file not found: {video_path}"

        frames_dir = host_video.parent / "qc_frames"
        is_mock = getattr(ctx.deps.settings, "test_model", False) or False
        report = await inspect_video_frames(host_video, frames_dir, mock=is_mock)
        _emit(ctx, "tool", {"name": "visual_qc_check", "passed": report.passed, "summary": report.summary})
        return report.model_dump_json(indent=2)



def concat_scene_videos(video_paths: list[Path], output_path: Path) -> tuple[bool, Path | list[Path], str]:
    """Concatenate multiple scene videos using ffmpeg. Falls back to individual videos on failure."""
    if not video_paths:
        return False, [], "No video files provided for concatenation"
    if len(video_paths) == 1:
        return True, video_paths[0], "Single video, no concat needed"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    list_file = output_path.parent / "concat_list.txt"
    try:
        lines = [f"file '{p.resolve().as_posix()}'" for p in video_paths]
        list_file.write_text("\n".join(lines), encoding="utf-8")
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(output_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            return True, output_path, "Concatenation succeeded"
        return False, video_paths, f"ffmpeg concat failed (code {res.returncode}): {res.stderr.strip()}"
    except Exception as exc:
        return False, video_paths, f"ffmpeg invocation error: {exc}"
    finally:
        if list_file.exists():
            try:
                list_file.unlink()
            except OSError:
                pass

