# Testing & Verification Rules

## 1. Test Command Execution
Always use the workspace virtual environment python executable to run tests:
```bash
.venv\Scripts\python.exe -m pytest
```

## 2. Optional Extras in Tests
If running without the `durable` extra (`kitaru-pydantic-ai`), exclude Kitaru wrapper unit tests using `-k`:
```bash
.venv\Scripts\python.exe -m pytest -k "not test_maybe_wrap_kitaru_when_enabled"
```

## 3. Offline Testing & Stubs
When verifying CLI or agent execution without live API keys or network connection, set offline test flags:
- `EDUCLAW_TEST_MODEL=1` or `--model test`
- `EDUCLAW_MEMORY_STUB=1`

## 4. Verification Mandate
Never mark a task complete without executing `.venv\Scripts\python.exe -m pytest` and ensuring zero failures on enabled features.
