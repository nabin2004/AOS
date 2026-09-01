# ManiBench — Development Guide

> Everything you need to set up, run, and understand the ManiBench evaluation pipeline.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Setup (≈ 5 min)](#quick-setup)
- [Project Layout](#project-layout)
- [Make Commands Reference](#make-commands-reference)
- [Running Evaluations](#running-evaluations)
- [Understanding the Pipeline](#understanding-the-pipeline)
- [Prompt Strategies](#prompt-strategies)
- [Metrics Explained](#metrics-explained)
- [Working with Results](#working-with-results)
- [Adding New Models](#adding-new-models)
- [Troubleshooting](#troubleshooting)
- [Time & Cost Estimates](#time--cost-estimates)

---

## Prerequisites

| Requirement | Minimum | Check |
|-------------|---------|-------|
| Python | 3.10+ | `python3 --version` |
| pip | 21+ | `pip --version` |
| make | any | `make --version` |
| LaTeX (optional) | texlive | `pdflatex --version` |
| FFmpeg (for Manim) | 4+ | `ffmpeg -version` |
| OpenRouter API key | — | [openrouter.ai/keys](https://openrouter.ai/keys) |

---

## Quick Setup

```bash
# 1. One command does it all: venv + deps + .env
make setup

# 2. Add your API key
nano .env   # paste your OPENROUTER_API_KEY=sk-or-v1-...

# 3. Activate the virtual environment
source .venv/bin/activate

# 4. Verify everything works
make check-env

# 5. Run a smoke test (1 API call, no rendering)
make quick-test
```

That's it. You're ready.

---

## Project Layout

```
ManiBench/
├── Makefile                            ← You are here
├── .env.example                        ← Template for API keys
├── .env                                ← Your local secrets (git-ignored)
├── requirements.txt                    ← Python dependencies
├── ManiBench_Pilot_Dataset.json        ← 12 problems (machine-readable)
├── ManiBench_Specification.md          ← Full research paper
├── ManiBench_Evaluation_Rubric.md      ← Scoring methodology
├── ManiBench_QuickStart.md             ← Quick reference
├── ManiBench_Prompt_Engineering_Guide.md ← Prompt strategies
├── DEVELOPMENT.md                      ← This file
├── README.md                           ← Overview & citation
│
├── evaluation/                         ← Python evaluation package
│   ├── __init__.py                     ← Package init + version
│   ├── __main__.py                     ← `python -m evaluation` entry
│   ├── run.py                          ← Main CLI: generation + metrics loop
│   ├── config.py                       ← Models, paths, GL patterns
│   ├── openrouter_client.py            ← OpenRouter API client
│   ├── openai_client.py                ← OpenAI-compatible / vLLM client
│   ├── prompts.py                      ← 5 prompt strategy builders
│   ├── analysis.py                     ← LaTeX/CSV/Markdown generators
│   ├── logger.py                       ← Structured JSONL logging
│   ├── metrics/
│   │   ├── __init__.py                 ← Re-exports all 4 metrics
│   │   ├── executability.py            ← Metric 1: syntax + render check
│   │   ├── version_conflict.py         ← Metric 2: GL/CE pattern scan
│   │   ├── alignment.py                ← Metric 3: visual event detection
│   │   └── coverage.py                 ← Metric 4: pedagogical elements
│   ├── generated_code/                 ← LLM outputs (per model/strategy)
│   ├── results/                        ← Raw JSON + analysis outputs
│   └── logs/                           ← JSONL experiment logs
│
└── raw_code/                           ← 3B1B's original ManimGL source
    ├── colliding_blocks_v2/            ← MB-001
    ├── nn/                             ← MB-002
    ├── convolutions/                   ← MB-003
    ├── eigen/                          ← MB-004
    ├── determinant/                    ← MB-005
    ├── clt/                            ← MB-006
    ├── med_test/                       ← MB-007
    ├── chain_rule/                     ← MB-008
    ├── ftc/                            ← MB-009
    ├── taylor_series/                  ← MB-010
    ├── hairy_ball/                     ← MB-011
    └── windmill/                       ← MB-012
```

---

## Make Commands Reference

### Setup Commands

| Command | What it does | When to use |
|---------|-------------|-------------|
| `make setup` | Creates venv, installs deps, copies `.env` | First time only |
| `make venv` | Creates `.venv/` directory | If venv is missing |
| `make install` | `pip install -r requirements.txt` | After adding deps |
| `make env` | Copies `.env.example` → `.env` | First time only |
| `make check-env` | Validates Python, deps, API key, Manim | Debugging setup issues |

### Evaluation Commands

| Command | API Calls | Time Est. | Description |
|---------|-----------|-----------|-------------|
| `make quick-test` | 1 | ~30s | GPT-4o on MB-005, 1 trial, no render |
| `make run` | 216 | 1–3 hrs | Full: 6 models × 12 problems × 3 trials |
| `make run-fast` | 216 | 30–60 min | Same but skips Manim rendering |
| `make run-cot` | 216 | 1–3 hrs | Full run with CoT prompting |
| `make run-single` | varies | varies | Specific model + problem |
| `make run-all-strategies` | 1,080 | 5–15 hrs | All 5 strategies back-to-back |

#### Customizing Runs

Override any default with CLI variables:

```bash
# Two models, three problems, one trial
make run MODELS="gpt-4o claude-sonnet-4" PROBLEMS="MB-001 MB-005 MB-007" TRIALS=1

# DeepSeek only, chain-of-thought, skip rendering
make run MODELS=deepseek-r1 STRATEGY=cot SKIP_RENDER=1

# Single problem deep dive (3 trials with rendering)
make run-single MODELS=gemini-2.5-pro PROBLEMS=MB-002 TRIALS=3

# Longer Manim timeout for complex scenes (Level 4-5)
make run PROBLEMS="MB-011" TIMEOUT=120
```

### Analysis Commands

| Command | Description |
|---------|-------------|
| `make analyze` | Analyze most recent results → LaTeX + CSV + Markdown |
| `make analyze-all` | Merge ALL results files and analyze together |
| `make list-results` | Show available results, logs, summaries |

### Utility Commands

| Command | Description |
|---------|-------------|
| `make validate` | Check dataset JSON integrity + package imports |
| `make dataset-info` | Print problem summary table |
| `make render-sample` | Render a test Manim scene (verifies FFmpeg + Manim) |
| `make list-models` | Query OpenRouter API for model availability |
| `make count-raw` | Count lines in raw_code/ reference files |

### Cleanup Commands

| Command | Removes | Safe? |
|---------|---------|-------|
| `make clean` | Generated code, logs, `__pycache__` | ✅ |
| `make clean-results` | Results JSON + analysis | ⚠️ Loses data |
| `make clean-media` | Manim `media/` renders | ✅ |
| `make clean-all` | Everything including venv | ⚠️ Full reset |

---

## Running Evaluations

### Workflow Overview

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Load 12    │───▶│  Build Prompt │───▶│  Call LLM    │───▶│  Extract     │
│   Problems   │    │  (strategy)   │    │  (OpenRouter) │    │  Code Block  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                    │
                    ┌──────────────┐    ┌──────────────┐    ┌──────▼───────┐
                    │  Save JSON   │◀───│  Compute     │◀───│  Save .py    │
                    │  Results     │    │  4 Metrics    │    │  to disk     │
                    └──────────────┘    └──────────────┘    └──────────────┘
```

### Step-by-Step

1. **Set API key**: `export OPENROUTER_API_KEY='sk-or-v1-...'` (or edit `.env`)

2. **Quick validation**:
   ```bash
   make check-env     # verify setup
   make quick-test    # 1 API call, confirms pipeline works
   ```

3. **Run evaluation**:
   ```bash
   make run                    # default: all models, zero-shot, 3 trials
   make run STRATEGY=cot       # use chain-of-thought
   make run TRIALS=1           # faster: 1 trial per combo
   ```

4. **Analyze results**:
   ```bash
   make analyze                # generates tables from latest results
   make list-results           # see what's available
   ```

5. **Find outputs**:
   - Raw results: `evaluation/results/results_<timestamp>.json`
   - Generated code: `evaluation/generated_code/<model>/<strategy>/MB-xxx_trial1.py`
   - Logs: `evaluation/logs/run_<timestamp>.jsonl`
   - Paper tables: `evaluation/results/analysis/`

---

## Understanding the Pipeline

### Data Flow

```
ManiBench_Pilot_Dataset.json
        │
        ▼
  ┌─────────────┐      ┌─────────────────┐
  │  prompts.py  │─────▶│ OpenRouter API   │
  │  (5 strategies)     │ (6 LLM models)   │
  └─────────────┘      └────────┬────────┘
                                │ generated code
                                ▼
                     ┌──────────────────┐
                     │    metrics/      │
                     ├──────────────────┤
                     │ 1. executability │ → syntax + render check
                     │ 2. version_conflict│ → regex GL pattern scan
                     │ 3. alignment     │ → AST visual event heuristics
                     │ 4. coverage      │ → pedagogical element density
                     └────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
      results/*.json   logs/*.jsonl   analysis/*.tex
```

### Key Modules

| Module | Purpose | Entry Point |
|--------|---------|-------------|
| `run.py` | Orchestrates the full loop | `main()` |
| `config.py` | Models, paths, GL patterns | imported everywhere |
| `openrouter_client.py` | HTTP client + code extraction | `OpenRouterClient.generate()` |
| `prompts.py` | Builds chat messages per strategy | `build_messages()` |
| `metrics/executability.py` | Syntax + render check | `compute_executability()` |
| `metrics/version_conflict.py` | GL pattern regex scan | `detect_version_conflicts()` |
| `metrics/alignment.py` | Visual event AST analysis | `compute_alignment()` |
| `metrics/coverage.py` | Pedagogical density check | `compute_coverage()` |
| `analysis.py` | LaTeX, CSV, Markdown output | `main()` |
| `logger.py` | Structured JSONL experiment log | `StructuredLogger` |

---

## Prompt Strategies

The evaluation supports 5 prompting approaches, each producing different chat message arrays:

| Strategy | System Prompt | User Prompt Style | Best For |
|----------|--------------|-------------------|----------|
| `zero_shot` | Generic Manim expert | Direct problem statement | Baseline |
| `few_shot` | Generic + 2 examples | Problem after examples | Improving output format |
| `cot` | Version-aware | 5-step analysis + code | Complex problems (L4-5) |
| `constraint` | Version-aware | Explicit event list + timing rules | Alignment-critical |
| `version_aware` | Detailed CE-only rules | Problem + GL trap warnings | Reducing version conflicts |

### When to Use Each

- **Research paper baseline**: `zero_shot`
- **Maximizing executability**: `version_aware`
- **Maximizing alignment**: `constraint` or `cot`
- **Comparing strategies**: `make run-all-strategies`

---

## Metrics Explained

### 1. Executability (Pass@1)

**Binary: does the code run?**

Checks (in order):
1. `ast.parse()` — valid Python syntax?
2. Import validation — uses `from manim import *` (not GL)?
3. Scene class detection — defines `class XYZ(Scene)`?
4. Manim render (subprocess, unless `--skip-render`) — runs without crash?

**Score**: `1` if all pass, `0` otherwise.

### 2. Version-Conflict Error Rate

**Static scan for GL-only patterns via regex.**

Scans code against 40+ patterns in `config.py` → `GL_ONLY_PATTERNS`:
- `ShowCreation(` → should be `Create(`
- `CONFIG = {` → should use `__init__`
- `self.frame.` → should be `self.camera.frame`
- `PiCreature`, `GlowDot`, `DieFace` → not in CE
- etc.

**Score**: `count_of_GL_matches / total_patterns_checked`

### 3. Alignment Score

**Weighted fraction of required visual events detected via AST heuristics.**

For each problem's `required_visual_events`, searches the AST + code text for:
- Method calls matching event patterns (e.g., `.move_to(`, `FadeIn(`)
- Object creations matching expected mobjects (e.g., `Dot(`, `Arrow(`)
- Temporal ordering of events in the `construct()` method

**Score**: `Σ(weight_i × detected_i) / Σ(weight_i)` — range [0.0, 1.0]

### 4. Coverage Score

**Density of pedagogical elements.**

Checks for presence of:
- Text labels (`Text(`, `MathTex(`, `Tex(`)
- Axis labels (`get_axis_labels`, `x_label=`)
- Color coding (`color=`, multiple colors used)
- Numeric values displayed
- Formulas and annotations

**Score**: `elements_found / elements_required` — range [0.0, 1.0]

---

## Working with Results

### Output Files

After a run, find these files:

```bash
make list-results   # shows everything

# Raw trial-level results (JSON array of records)
evaluation/results/results_20260220_143052.json

# Structured experiment log (JSONL, one event per line)
evaluation/logs/run_20260220_143052.jsonl

# Aggregated summary
evaluation/logs/run_20260220_143052_summary.json

# Generated code files
evaluation/generated_code/GPT-4o/zero_shot/MB-005_trial1.py
```

### Generating Paper Tables

```bash
# From latest run
make analyze

# From all runs (merged)
make analyze-all

# Manual
python -m evaluation.analysis --results evaluation/results/results_XXXXX.json
```

This produces:
- `table_model_performance.tex` — Table 1 for paper
- `table_grid_exec.tex` / `_align` / `_cov` / `_vc` — Model×Problem grids
- `table_strategy_comparison.tex` — Strategy comparison
- `results_flat.csv` — For matplotlib/seaborn plots
- `evaluation_report.md` — Markdown summary

### Inspecting Generated Code

Browse the generated code to understand model behavior:

```bash
# See all generated files for GPT-4o
ls evaluation/generated_code/GPT-4o/zero_shot/

# Read a specific generation
cat evaluation/generated_code/GPT-4o/zero_shot/MB-005_trial1.py

# Try rendering it
manim -ql evaluation/generated_code/GPT-4o/zero_shot/MB-005_trial1.py
```

---

## Adding New Models

### OpenRouter / Inference.net

Edit `evaluation/config.py` → `DEFAULT_MODELS` (or `INFERENCE_MODELS`):

```python
DEFAULT_MODELS.append(
    ModelSpec(
        id="mistralai/mistral-large-latest",   # OpenRouter model ID
        short_name="Mistral-Large",             # For tables & filenames
        provider="Mistral",                     # Paper attribution
        max_tokens=8192,
        temperature=0.0,
    )
)
```

Find model IDs at [openrouter.ai/models](https://openrouter.ai/models) or via `make list-models`.

### OpenAI-compatible / vLLM

No roster edit needed. Point at any OpenAI-compatible chat completions server:

```bash
# Via CLI
python -m evaluation.run --provider openai \
  --base-url http://localhost:8000/v1 \
  --models Qwen/Qwen2.5-Coder-7B-Instruct \
  --problems MB-001 --trials 1

# Via Makefile
make run-openai BASE_URL=http://localhost:8000/v1 \
  MODELS="Qwen/Qwen2.5-Coder-7B-Instruct" PROBLEMS=MB-001 TRIALS=1

# Or set OPENAI_BASE_URL in .env, then:
make run PROVIDER=openai MODELS="my-served-model" TRIALS=1
```

`--models` values are the served model IDs (as reported by `/v1/models`). `OPENAI_API_KEY` is optional for local unauthenticated servers. List remote models with `make openai-list-models` (requires `OPENAI_BASE_URL` or `BASE_URL`).

---

## Troubleshooting

### "OPENROUTER_API_KEY not set" / OpenRouter token

```bash
# Option 1: environment variable
export OPENROUTER_API_KEY='sk-or-v1-your-key'

# Option 2: .env file
echo "OPENROUTER_API_KEY=sk-or-v1-your-key" > .env

# Option 3: pass the token on the CLI (overrides env)
python -m evaluation.run --api-key sk-or-v1-your-key --models claude-sonnet-4 --trials 1

# Then verify
make check-env
```

### "Manim CE not importable"

```bash
# Ensure you're in the venv
source .venv/bin/activate
make install

# Check FFmpeg (required by Manim)
ffmpeg -version    # must be installed
sudo apt install ffmpeg   # Ubuntu/Debian
brew install ffmpeg        # macOS
```

### "HTTP 429: Rate limited"

The client auto-retries with backoff. If you hit persistent limits:

```bash
# Reduce parallelism — run fewer models at once
make run MODELS=gpt-4o TRIALS=1

# Or increase retry delay in config.py
RETRY_DELAY = 10   # seconds between retries
```

### "Timeout rendering scene"

Complex scenes (Level 4-5) may need more time:

```bash
make run TIMEOUT=120 PROBLEMS="MB-011"   # 2 minutes
make run SKIP_RENDER=1                    # or skip rendering entirely
```

### Clean slate

```bash
make clean-all   # removes venv + all outputs
make setup       # start fresh
```

---

## Time & Cost Estimates

### Time per Run Configuration

| Configuration | API Calls | Est. Time | Est. Cost* |
|---------------|-----------|-----------|-----------|
| `make quick-test` | 1 | 30 sec | < $0.01 |
| `make run MODELS=gpt-4o TRIALS=1` | 12 | 5–10 min | ~$0.50 |
| `make run TRIALS=1` | 72 | 30–60 min | ~$3–5 |
| `make run` (default: 3 trials) | 216 | 1–3 hrs | ~$10–15 |
| `make run-all-strategies` | 1,080 | 5–15 hrs | ~$50–75 |

*Costs are rough estimates based on OpenRouter pricing as of Feb 2026. Actual costs vary by model.

### Per-Model Cost Factors

| Model | Relative Cost | Relative Speed |
|-------|--------------|----------------|
| GPT-4o | $$$ | Fast |
| Claude Sonnet 4 | $$$ | Fast |
| Gemini 2.5 Pro | $$ | Fast |
| DeepSeek-R1 | $ | Medium |
| Llama 4 Maverick | $ | Medium |
| Qwen 2.5 Coder | $ | Fast |

### Manim Rendering Time

- Level 2 problems (Determinant, Bayes): ~10–30 sec per render
- Level 3 problems (Gradient Descent, Convolution): ~30–90 sec per render
- Level 4 problems (Taylor, Eigenvectors): ~1–3 min per render
- Level 5 problems (Hairy Ball): ~2–5 min per render (often fails/timeouts)

Use `make run-fast` (or `SKIP_RENDER=1`) to bypass rendering for quick iteration.

---

## Common Workflows

### "I just want to see if things work"

```bash
make setup && make quick-test
```

### "Run the full paper evaluation"

```bash
make run                # zero-shot baseline
make run STRATEGY=cot   # chain-of-thought comparison
make analyze-all        # combined report
```

### "Test a new model"

```bash
# 1. Add to config.py (see Adding New Models above)
# 2. Quick test
make run MODELS=my-new-model PROBLEMS=MB-005 TRIALS=1
# 3. Full run
make run MODELS=my-new-model
```

### "Reproduce the paper results"

```bash
make run STRATEGY=zero_shot
make run STRATEGY=cot
make run STRATEGY=version_aware
make analyze-all
# → Tables in evaluation/results/analysis/
```

---

*Last Updated: 2026-02-20*
