from pathlib import Path
from types import SimpleNamespace

from educlaw.lsp.ty import LspClient, TyClient


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


def test_find_definition_class_and_func(tmp_path: Path) -> None:
    client = LspClient(tmp_path)
    mod = tmp_path / "sample.py"
    mod.write_text(
        'class Helper:\n    """Helper class."""\n    pass\n\n'
        'def compute(val: int) -> int:\n    """Compute something."""\n    return val * 2\n',
        encoding="utf-8",
    )

    class_def = client.find_definition("Helper")
    assert "Found 'Helper' [Class] in sample.py" in class_def
    assert "Docstring: Helper class." in class_def

    func_def = client.find_definition("compute")
    assert "Found 'compute' [Function] in sample.py" in func_def
    assert "def compute(val: int) -> int" in func_def


def test_file_symbols(tmp_path: Path) -> None:
    client = LspClient(tmp_path)
    mod = tmp_path / "calc.py"
    mod.write_text(
        "class Calculator:\n    pass\n\n"
        "async def async_run(data: str) -> None:\n    pass\n",
        encoding="utf-8",
    )

    result = client.file_symbols(mod)
    assert "Symbols in calc.py:" in result
    assert "[Class] Calculator" in result
    assert "[AsyncFunction] async_run" in result


def test_workspace_symbols(tmp_path: Path) -> None:
    client = LspClient(tmp_path)
    file1 = tmp_path / "a.py"
    file1.write_text("def alpha_function(): pass\n", encoding="utf-8")
    file2 = tmp_path / "b.py"
    file2.write_text("class BetaClass: pass\n", encoding="utf-8")

    all_symbols = client.workspace_symbols()
    assert "Workspace Symbols (2 found):" in all_symbols
    assert "alpha_function" in all_symbols
    assert "BetaClass" in all_symbols

    filtered = client.workspace_symbols("alpha")
    assert "alpha_function" in filtered
    assert "BetaClass" not in filtered
