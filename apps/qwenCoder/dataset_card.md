---
license: apache-2.0
task_categories:
  - text-generation
language:
  - en
tags:
  - manim
  - agent-trajectory
  - tool-calling
  - qwen
  - aos
---

# AOS-Qwen-Trajectories

Agent trajectories from the AOS PydanticAI Code Agent (`animus animate`), intended for
Qwen2.5-Coder tool-call SFT, DPO, and GRPO.

## Files

| Path | Format | Use |
|------|--------|-----|
| `trajectories.jsonl` | Raw `TrajectoryRecord` | Analysis / rebuild |
| `tool_trace/train.jsonl` | OpenAI multi-turn `messages` + tools | **SFT** |
| `tool_trace/val.jsonl` | Same | Validation |
| `preference/train.jsonl` | `{prompt, chosen, rejected}` | **DPO** |
| `preference/val.jsonl` | Same | Validation |

## Raw schema

- `user_prompt`, `success`, `has_audio`, `final_code`
- `trajectory[]`: `{tool_name, input, output, is_error}`
- `run_dir`, `timestamp`, `usage`

Gold filter for video+audio: `success=true` and `has_audio=true`.

## Preference schema

```json
{
  "prompt": "...",
  "chosen": {"messages": [...]},
  "rejected": {"messages": [...]},
  "metadata": {
    "chosen_run_dir": "...",
    "rejected_reason": "compile_fail|no_audio|synthesized_codemode_violation"
  }
}
```

## Collect locally

```bash
bash apps/qwenCoder/collect_and_export.sh
PUSH=1 bash apps/qwenCoder/collect_and_export.sh
```
