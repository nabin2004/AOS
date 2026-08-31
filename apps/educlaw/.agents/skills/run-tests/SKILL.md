---
name: run-tests
description: Run the EduClaw test suite safely using the virtual environment python runner.
---

# Run EduClaw Test Suite

Use this skill whenever you need to execute tests in the `educlaw` workspace.

## Command

Run pytest using the local virtual environment:

```powershell
.venv\Scripts\python.exe -m pytest
```

If optional extras like `kitaru-pydantic-ai` are not installed, run:

```powershell
.venv\Scripts\python.exe -m pytest -k "not test_maybe_wrap_kitaru_when_enabled"
```

## Running Smoke Evals

To run the offline smoke evals:

```powershell
.venv\Scripts\python.exe -m evals.smoke
```
