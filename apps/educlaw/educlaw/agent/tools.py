"""Sandbox, render, and LSP tools registered on the EduClaw agent."""

from __future__ import annotations

from pydantic_ai import Agent, RunContext

from educlaw.agent.deps import AgentDeps
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
