from pathlib import Path
from types import SimpleNamespace

from educlaw.lsp.ty import TyClient


def test_syntax_ok_and_error(tmp_path: Path) -> None:
    client = TyClient(tmp_path)
    good = tmp_path / "ok.py"
    good.write_text("x = 1\n", encoding="utf-8")
    assert client.syntax_check(good) == "syntax ok"
    bad = tmp_path / "bad.py"
    bad.write_text("def (\n", encoding="utf-8")
    assert "syntax error" in client.syntax_check(bad)


def test_diagnostics_uses_runner(tmp_path: Path) -> None:
    client = TyClient(tmp_path)
    path = tmp_path / "ok.py"
    path.write_text("x = 1\n", encoding="utf-8")

    def runner(_argv):
        return SimpleNamespace(returncode=0, stdout="ty check ok\n", stderr="")

    assert client.diagnostics(path, runner=runner) == "ty check ok"


def test_after_write_skips_non_python(tmp_path: Path) -> None:
    client = TyClient(tmp_path)
    path = tmp_path / "notes.txt"
    path.write_text("hi", encoding="utf-8")
    assert client.after_write(path) == ""
