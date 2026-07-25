# SFT data generation

This folder holds synthetic prompts and batch scripts for collecting **Code Agent** traces used in LLM finetuning.

See the full workflow in the parent [README](../README.md#sft-data-collection-code-agent).

## Files

| File | Purpose |
|------|---------|
| `topics.txt` | Topic seeds for `generate_prompts.py` (one topic per line) |
| `additional_topics.txt` | Extra topic seeds (bare names; wrappers are stripped on load) |
| `andrej_karpathy.txt` | ML / education topic seeds |
| `andrej_karpathy_400.txt` | 400 Karpathy/Micrograd→torch.nn Manim seeds (from `_andrej_karpathy.txt`) |
| `manim_curriculum_200.txt` | 200 Manim curriculum topics (algebra → discrete math) |
| `generate_prompts.py` | Batched LLM user requests → `prompts.jsonl` |
| `prompts.jsonl` | Prompt bank (`{"index", "topic", "prompt"}` per line) |
| `prompts_curriculum_200.jsonl` | Dedicated bank for the curriculum-200 wave |
| `prompts_andrej_400.jsonl` | Dedicated bank for the Karpathy-400 wave |
| `prompts.jsonl.bak` | Backup of previous bank (created by `--no-resume`) |
| `collect_traces.py` | Batch-run `agent_graph` over `prompts.jsonl` |
| `run_waves.sh` | Loop `collect_traces` until unique success target |
| `status.py` | Progress / ETA report vs compile_ok target |
| `batch_runs.jsonl` | Append-only manifest (created by `collect_traces.py`) |
| `batch_summary.json` | Last batch stats (created by `collect_traces.py`) |

## Scale target (multi-thousand LoRA SFT)

| Stage | Target |
|-------|--------|
| Prompt bank | ~8,000 prompts |
| Deduped `compile_ok` trajectories | ~5,000 unique prompts |
| Wall clock (rough) | 1–2 weeks @ concurrency 2–4 |

Data is **synthetic prompts + real agent + Manim compile** (not fabricated tool traces).

## Quick start

From `apps/agents`:

```bash
# 1) Expand prompts from all topic banks (resume-safe by default)
# Fresh rebuild: add --no-resume (backs up existing file to prompts.jsonl.bak)
uv run python sft_data_gen/generate_prompts.py \
  --num 8000 \
  --output sft_data_gen/prompts.jsonl \
  --concurrency 20 \
  --batch-size 8 \
  --verify \
  --topics sft_data_gen/topics.txt \
            sft_data_gen/additional_topics.txt \
            sft_data_gen/andrej_karpathy.txt

# 2) Check progress anytime
uv run python sft_data_gen/status.py --target 5000 --concurrency 4

# 3a) Single wave — recommended fast batch
uv run python sft_data_gen/collect_traces.py \
  --limit 200 \
  --fast \
  --convert-after-local \
  --resume \
  --concurrency 4

# 3b) Continuous waves until target (tmux/systemd)
chmod +x sft_data_gen/run_waves.sh
TARGET=5000 CONCURRENCY=4 LIMIT=200 ./sft_data_gen/run_waves.sh

# 4) Or export separately after a batch
uv run python export_local_sft.py

# 5) Publish to Hugging Face (optional)
export HF_TOKEN=hf_...   # write token; never commit
cd ../sft && uv run python upload_dataset.py
```

## Curriculum wave (next 200 prompts)

One naturalistic user request per topic from `manim_curriculum_200.txt` (algebra → discrete math). Uses `--exhaust-topics` so each seed appears exactly once, written to a dedicated file (does not fight resume against the 8k main bank).

```bash
cd apps/agents

# Generate exactly 200 prompts (one per curriculum topic)
uv run python sft_data_gen/generate_prompts.py \
  --num 200 \
  --exhaust-topics \
  --topics sft_data_gen/manim_curriculum_200.txt \
  --output sft_data_gen/prompts_curriculum_200.jsonl \
  --no-resume \
  --concurrency 20 \
  --batch-size 8 \
  --verify

# Collect Code Agent traces from that bank
uv run python sft_data_gen/collect_traces.py \
  --prompts sft_data_gen/prompts_curriculum_200.jsonl \
  --limit 200 \
  --fast \
  --convert-after-local \
  --resume \
  --concurrency 4
```

Optional: append into the main bank later with
`cat sft_data_gen/prompts_curriculum_200.jsonl >> sft_data_gen/prompts.jsonl`
(re-index if you rely on contiguous `index` values).

## Karpathy wave (next 400 prompts)

One naturalistic user request per seed from `andrej_karpathy_400.txt` (Micrograd → torch.nn / DL process), extracted from `_andrej_karpathy.txt`. Uses `--exhaust-topics` so each seed appears exactly once.

```bash
cd apps/agents

# Generate exactly 400 user requests (one per seed)
uv run python sft_data_gen/generate_prompts.py \
  --num 400 \
  --exhaust-topics \
  --topics sft_data_gen/andrej_karpathy_400.txt \
  --output sft_data_gen/prompts_andrej_400.jsonl \
  --no-resume \
  --concurrency 20 \
  --batch-size 8 \
  --verify

# Collect Code Agent traces from that bank
uv run python sft_data_gen/collect_traces.py \
  --prompts sft_data_gen/prompts_andrej_400.jsonl \
  --limit 400 \
  --fast \
  --convert-after-local \
  --resume \
  --concurrency 4
```

Optional merge: `cat sft_data_gen/prompts_andrej_400.jsonl >> sft_data_gen/prompts.jsonl`.

Prompt generation uses batched OpenRouter calls (`--batch-size`, default 8) and
enforces teaching vs learning voice: instructor frames must say **teaching**;
student frames may say **learning** only about the subject, never an audience.
A quality gate rejects `I'm learning … students` / course-frame swaps and meta leaks.

`--fast` disables Logfire/DBOS (no OTLP timeout stalls), skips narration, preloads the Manim doc RAG index. Default concurrency is **2**; use **4** for scale-up if OpenRouter + local Manim stay stable.

Use `tool_trace*.jsonl` under `export_traces/coder_sft/` for tool-calling finetune data. Published copies live at [nabin2004/AOS-Trajectories](https://huggingface.co/datasets/nabin2004/AOS-Trajectories).

## Ops notes (waves / cost / concurrency)

1. **Wave size:** `--limit 200–500` per wave, or leave `run_waves.sh` running under `tmux`.
2. **Concurrency ladder:** start at `4` → drop to `2` or `1` on rate limits / Manim OOM → raise only after a healthy `--limit 20` stress test.
3. **Resume:** default `--resume` skips indices already `ok` in `batch_runs.jsonl`.
4. **Retries:** re-run without `--skip-failed` to retry failures; only pass `--skip-failed` when abandoning bad indices.
5. **Cost:** each example ≈ classify + plan + coder (OpenRouter) + Manim compile. Budget for ~5.5k attempts at ~90% `compile_ok` to land ~5k successes.
6. **Quality:** trainer keeps `success: true` + non-empty `final_code`; export keeps shortest successful trajectory per `user_prompt`.
7. **Monitor:** `uv run python sft_data_gen/status.py` after each wave; watch `batch_summary.json` and disk under `workspace/coder_runs/`.

## Notes

- Topic files are **not** fed directly to the agent — they only seed prompt generation.
- Each successful run writes artifacts under `workspace/coder_runs/{timestamp}-{slug}/`.
- Local offline traces: `workspace/coder_runs/*/traces/messages.json` and `trajectory.json`.
- Global training bank: `training_data/trajectories.jsonl` (append-only).
- Dedup on export: one row per `user_prompt`, shortest successful trajectory wins.
- Re-enable Logfire for a batch: `AOS_LOGFIRE=1 uv run python sft_data_gen/collect_traces.py ...`

### Optional: Logfire export

If you also send spans to Logfire for production observability:

```bash
uv run python export_coder_sft.py --days 30
```

Requires `LOGFIRE_READ_TOKEN` in `export_traces/.env`.
