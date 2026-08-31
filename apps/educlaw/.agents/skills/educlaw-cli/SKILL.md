---
name: educlaw-cli
description: Run and inspect EduClaw CLI commands in offline or interactive mode.
---

# EduClaw CLI Runbook

Use this skill when testing or executing `educlaw` subcommands.

## Offline / Dry-Run Commands

Always run CLI tests with offline stubs (`EDUCLAW_TEST_MODEL=1` and `EDUCLAW_MEMORY_STUB=1`) to avoid live API token usage:

### 1. Doctor & Configuration Check
```powershell
$env:EDUCLAW_TEST_MODEL="1"; $env:EDUCLAW_MEMORY_STUB="1"
.venv\Scripts\python.exe -m educlaw.cli doctor
.venv\Scripts\python.exe -m educlaw.cli config
```

### 2. Single-shot Run Execution
```powershell
.venv\Scripts\python.exe -m educlaw.cli --model test --yes run "Render a circle scene"
```

### 3. Memory Inspection
```powershell
.venv\Scripts\python.exe -m educlaw.cli memory show
```
