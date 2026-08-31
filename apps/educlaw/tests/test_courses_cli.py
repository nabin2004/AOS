from pathlib import Path
from typer.testing import CliRunner

from educlaw.cli import app


runner = CliRunner()


def test_cli_course_new_and_list(tmp_path):
    result = runner.invoke(
        app,
        [
            "course",
            "new",
            "Linear Algebra Fundamentals",
            "--lectures",
            "2",
            "--no-render",
            "--model",
            "test",
            "--cwd",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Course Curriculum Generated" in result.output

    # Test list command
    list_res = runner.invoke(app, ["course", "list", "--cwd", str(tmp_path)])
    assert list_res.exit_code == 0, list_res.output
    assert "educational-course" in list_res.output.lower() or "Educational Course" in list_res.output


def test_cli_course_show_and_export(tmp_path):
    # Create course first
    create_res = runner.invoke(
        app,
        [
            "course",
            "new",
            "Quantum Optics",
            "--lectures",
            "2",
            "--no-render",
            "--model",
            "test",
            "--cwd",
            str(tmp_path),
        ],
    )
    assert create_res.exit_code == 0, create_res.output

    # Show command
    show_res = runner.invoke(app, ["course", "show", "educational-course", "--cwd", str(tmp_path)])
    assert show_res.exit_code == 0, show_res.output
    assert "Educational Course" in show_res.output or "educational-course" in show_res.output

    # Export command
    export_res = runner.invoke(app, ["course", "export", "educational-course", "--cwd", str(tmp_path)])
    assert export_res.exit_code == 0, export_res.output
    assert "exported to" in export_res.output.lower()


def test_cli_animate_mode_course(tmp_path):
    result = runner.invoke(
        app,
        [
            "animate",
            "Differential Equations",
            "--mode",
            "course",
            "--lectures",
            "2",
            "--no-render",
            "--model",
            "test",
            "--cwd",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Starting EduClaw Course Engine" in result.output
    assert "Course Curriculum Generated" in result.output
