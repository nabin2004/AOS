# SFT data generation

This folder holds synthetic prompts and batch scripts for collecting **Code Agent** traces used in LLM finetuning.

See the full workflow in the parent [README](../README.md#sft-data-collection-code-agent).

## Files

| File | Purpose |
|------|---------|
| `topics.txt` | Topic seeds for `generate_prompts.py` (one topic per line) |
| `additional_topics.txt` | Extra topic seeds |
| `generate_prompts.py` | LLM-generated user requests → `prompts.jsonl` |
| `prompts.jsonl` | Prompt bank (`{"index", "prompt", ...}` per line) |
| `collect_traces.py` | Batch-run `agent_graph` over `prompts.jsonl` |
| `batch_runs.jsonl` | Append-only manifest (created by `collect_traces.py`) |
| `batch_summary.json` | Last batch stats (created by `collect_traces.py`) |

## Quick start

From `apps/agents`:

```bash
# 1) Optional: generate more prompts from topics
uv run python sft_data_gen/generate_prompts.py --num 100 --topics sft_data_gen/topics.txt

# 2) Collect traces — recommended fast batch
uv run python sft_data_gen/collect_traces.py --limit 100 --fast --convert-after-local --resume

# 3) Or export separately after a batch
uv run python export_local_sft.py
```

`--fast` disables Logfire/DBOS (no OTLP timeout stalls), skips narration, preloads the Manim doc RAG index, and runs **2 prompts in parallel** by default.

Use `tool_trace*.jsonl` under `export_traces/coder_sft/` for tool-calling finetune data.

## Notes

- `topics.txt` is **not** fed directly to the agent — it only seeds prompt generation.
- Each successful run writes artifacts under `workspace/coder_runs/{timestamp}-{slug}/`.
- Local offline traces: `workspace/coder_runs/*/traces/messages.json` and `trajectory.json`.
- Global training bank: `training_data/trajectories.jsonl` (append-only).
- Re-run with `--resume` (default) to skip indices already marked `ok` in `batch_runs.jsonl`.
- Dedup on export: one row per `user_prompt`, shortest successful trajectory wins.
- Lower parallelism if you hit rate limits: `--concurrency 1`.
- Re-enable Logfire for a batch: `AOS_LOGFIRE=1 uv run python sft_data_gen/collect_traces.py ...`

### Optional: Logfire export

If you also send spans to Logfire for production observability:

```bash
uv run python export_coder_sft.py --days 30
```

Requires `LOGFIRE_READ_TOKEN` in `export_traces/.env`.
