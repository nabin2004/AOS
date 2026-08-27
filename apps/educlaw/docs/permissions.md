# Permissions

Modes (Claude Code-shaped), via `EDUCLAW_PERMISSION_MODE` or `--yes`:

| Mode | Asks before |
|------|-------------|
| `default` | `bash`, `render`, `destructive` |
| `edit` | those plus `write` |
| `auto` | nothing |

`read` is always allowed. Destructive classification covers `rm`, `rm -rf`, `git reset --hard`, `git clean`, `mkfs`, `dd if=`, `format`, `shred`.

Headless CI: `educlaw --headless --yes -p "..."` or `EDUCLAW_PERMISSION_MODE=auto`.

Interactive: REPL prompts `allow? [y/N]`. TUI uses `/yes` and `/no` for a pending gate future.
