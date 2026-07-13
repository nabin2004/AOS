# store

Local persistence layer shared by `apps/cli.py` and `apps/tui`.

Since the real generation pipeline in `apps/agents` isn't wired up yet, `create_lecture`
and `create_course` build a mock-but-schema-valid `ir.LectureIR` (the real pydantic IR from
`packages/ir`) and persist it as JSON under `<repo root>/data/`. Swap `generator.py`'s
internals for a real pipeline call later without touching the CLI/TUI.
