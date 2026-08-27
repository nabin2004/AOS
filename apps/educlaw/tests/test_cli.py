"""Unit tests for Typer and Rich CLI in educlaw.cli."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

from educlaw.cli import (
    HELP,
    _handle_slash,
    _print_emit,
    app,
    build_parser,
    main,
    print_slash_help,
)

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "EduClaw" in result.output
    assert "repl" in result.output
    assert "doctor" in result.output
    assert "config" in result.output
    assert "memory" in result.output


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "EduClaw version" in result.output

    result2 = runner.invoke(app, ["version"])
    assert result2.exit_code == 0
    assert "EduClaw version" in result2.output


def test_cli_config() -> None:
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "Active EduClaw Settings" in result.output
    assert "EDUCLAW_MODEL" in result.output


def test_cli_doctor(tmp_path: Path) -> None:
    result = runner.invoke(app, ["doctor", "--cwd", str(tmp_path)])
    assert result.exit_code == 0
    assert "EduClaw Health & Environment Check" in result.output
    assert "Python Version" in result.output
    assert "Agent Model" in result.output


def test_cli_headless_missing_prompt() -> None:
    result = runner.invoke(app, ["--headless"])
    assert result.exit_code == 2
    assert "Headless mode requires a prompt" in result.output


def test_cli_run_test_model(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["run", "Hello world", "--model", "test", "--yes", "--cwd", str(tmp_path), "--raw"],
    )
    assert result.exit_code == 0
    assert "ok" in result.output


def test_legacy_headless_flag(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["--headless", "-p", "Legacy prompt", "--model", "test", "--yes", "--cwd", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "ok" in result.output


def test_print_slash_help() -> None:
    c = Console(record=True)
    print_slash_help(c)
    out = c.export_text()
    assert "/compact" in out
    assert "/clear" in out
    assert "/memory" in out
    assert "/curate" in out


def test_print_emit() -> None:
    c = Console(record=True)
    _print_emit("abort", "aborted", target_console=c)
    _print_emit("memory_skip", "no client", target_console=c)
    _print_emit("permission_required", "run bash", target_console=c)
    _print_emit("tool", "bash('ls')", target_console=c)
    _print_emit("other", "payload", target_console=c)

    out = c.export_text()
    assert "[ABORT]" in out
    assert "[WARN]" in out
    assert "Permission Required" in out
    assert "[TOOL]" in out


@pytest.mark.asyncio
async def test_handle_slash_commands() -> None:
    handler = MagicMock()
    handler.full_compaction = AsyncMock()
    handler.deps.memory.strategy = AsyncMock(return_value="strategy-test")
    handler.deps.memory.retrieve = AsyncMock(return_value="retrieve-test")
    handler.deps.memory.curate = AsyncMock(return_value=MagicMock(contradictions_found=0))
    handler.deps.gate.answer.return_value = True

    c = Console(record=True)

    # quit / exit
    assert await _handle_slash(handler, "/quit", target_console=c) is True
    assert await _handle_slash(handler, "/exit", target_console=c) is True
    assert await _handle_slash(handler, "/q", target_console=c) is True

    # help
    assert await _handle_slash(handler, "/help", target_console=c) is False

    # clear
    assert await _handle_slash(handler, "/clear", target_console=c) is False
    handler.clear.assert_called_once()

    # compact
    assert await _handle_slash(handler, "/compact", target_console=c) is False
    handler.full_compaction.assert_awaited_once()

    # memory
    assert await _handle_slash(handler, "/memory search-term", target_console=c) is False
    handler.deps.memory.strategy.assert_awaited_once()
    handler.deps.memory.retrieve.assert_awaited_once_with("search-term")

    # curate
    assert await _handle_slash(handler, "/curate", target_console=c) is False
    handler.deps.memory.curate.assert_awaited_once()

    # abort
    assert await _handle_slash(handler, "/abort", target_console=c) is False
    handler.deps.steering.push.assert_called_with("/abort", kind="abort")

    # steer
    assert await _handle_slash(handler, "/steer guide agent", target_console=c) is False
    handler.deps.steering.push.assert_called_with("guide agent", kind="steer")

    # yes
    assert await _handle_slash(handler, "/yes", target_console=c) is False
    handler.deps.gate.answer.assert_called_with(True)

    # no
    handler.deps.gate.answer.return_value = True
    assert await _handle_slash(handler, "/no", target_console=c) is False
    handler.deps.gate.answer.assert_called_with(False)

    # unknown
    assert await _handle_slash(handler, "/unknown", target_console=c) is False


def test_main_wrapper_exit_code() -> None:
    assert main(["--version"]) == 0
    assert main(["--headless"]) == 2


def test_legacy_parser() -> None:
    parser = build_parser()
    args = parser.parse_args(["--headless", "-p", "foo", "--yes"])
    assert args.headless is True
    assert args.prompt == "foo"
    assert args.yes is True
