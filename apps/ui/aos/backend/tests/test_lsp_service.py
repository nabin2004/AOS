import pytest
from app.services.lsp_service import (
    LspDiagnostic,
    LspDiagnosticReport,
    run_pyright_lsp,
)


def test_lsp_diagnostic_properties() -> None:
    diag_err = LspDiagnostic(
        file="scene.py",
        severity="error",
        message="Cannot access attribute 'clear' for class 'VGroup'",
        line=233,
        character=13,
        rule="reportAttributeAccessIssue",
    )
    assert diag_err.is_error is True
    assert diag_err.is_warning is False
    assert "Line 233:13 (ERROR)" in diag_err.format_line()

    diag_warn = LspDiagnostic(
        file="scene.py",
        severity="warning",
        message="Unsupported escape sequence",
        line=10,
        character=5,
        rule="reportInvalidStringEscapeSequence",
    )
    assert diag_warn.is_warning is True
    assert diag_warn.is_error is False


def test_lsp_report_feedback_formatting() -> None:
    diags = [
        LspDiagnostic(
            file="scene.py",
            severity="error",
            message="Cannot access attribute 'frame' for class 'Camera'",
            line=588,
            character=25,
            rule="reportAttributeAccessIssue",
        ),
        LspDiagnostic(
            file="scene.py",
            severity="warning",
            message="Wildcard import",
            line=1,
            character=1,
            rule="reportWildcardImportFrom",
        ),
    ]
    report = LspDiagnosticReport(success=True, diagnostics=diags)
    assert report.has_errors is True
    assert report.error_count == 1
    assert report.warning_count == 1

    feedback = report.format_feedback()
    assert "[LINE 588:25] ERROR: Cannot access attribute 'frame'" in feedback
    assert "reportAttributeAccessIssue" in feedback


def test_lsp_runs_on_type_error_code_string() -> None:
    broken_code = "val: int = 'hello_world'\nprint(val)\n"
    report = run_pyright_lsp(broken_code, is_code=True)
    if report.success:
        assert report.has_errors is True
        messages = [d.message for d in report.diagnostics]
        assert any("not assignable" in m.lower() for m in messages)
