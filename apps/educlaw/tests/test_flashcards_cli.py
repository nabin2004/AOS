from pathlib import Path
from typer.testing import CliRunner

from educlaw.cli import app


runner = CliRunner()


def test_cli_flashcards_new(tmp_path):
    output_anki = tmp_path / "fourier.anki.txt"
    result = runner.invoke(
        app,
        [
            "flashcards",
            "new",
            "Fourier Analysis",
            "--format",
            "anki",
            "--output",
            str(output_anki),
            "--model",
            "test",
            "--cwd",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert output_anki.exists()
    content = output_anki.read_text(encoding="utf-8")
    assert "#separator:tab" in content
    assert "Flashcards Preview" in result.output


def test_cli_course_flashcards(tmp_path):
    # 1. Create a course first
    create_res = runner.invoke(
        app,
        [
            "course",
            "new",
            "Linear Algebra",
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

    # 2. Generate flashcards for Lecture 1 of the course
    fc_res = runner.invoke(
        app,
        [
            "course",
            "flashcards",
            "educational-course",
            "--lecture",
            "1",
            "--format",
            "anki",
            "--model",
            "test",
            "--cwd",
            str(tmp_path),
        ],
    )
    assert fc_res.exit_code == 0, fc_res.output
    assert "Generated" in fc_res.output

    lec1_fc = tmp_path / ".educlaw" / "courses" / "educational-course" / "lecture_01" / "flashcards.anki.txt"
    assert lec1_fc.exists()
    assert "#separator:tab" in lec1_fc.read_text(encoding="utf-8")
