# ══════════════════════════════════════════════════════════════════════════
# ManiBench — Makefile
# ══════════════════════════════════════════════════════════════════════════
# Run `make help` to see all available commands.
#
# Quick start:
#   make setup          # one-time: venv + deps + .env
#   make quick-test     # smoke-test: 1 model, 1 problem, 1 trial
#   make run            # full evaluation: 6 models × 12 problems × 3 trials
#   make analyze        # generate LaTeX tables, CSV, Markdown report
# ══════════════════════════════════════════════════════════════════════════

# ── Config ────────────────────────────────────────────────────────────────
SHELL        := /bin/bash
PYTHON       ?= python3
VENV         := .venv
PIP          := $(VENV)/bin/pip
PY           := $(VENV)/bin/python
MANIM        := $(VENV)/bin/manim

# Evaluation defaults (override on CLI: make run TRIALS=1 MODELS="gpt-4o")
TRIALS       ?= 3
STRATEGY     ?= zero_shot
TIMEOUT      ?= 60
SEED         ?= 42
MODELS       ?=
PROBLEMS     ?=
SKIP_RENDER  ?=
PROVIDER     ?= openrouter
BASE_URL     ?=
API_KEY      ?=

# Directories
RESULTS_DIR  := evaluation/results
LOGS_DIR     := evaluation/logs
GEN_CODE_DIR := evaluation/generated_code
ANALYSIS_DIR := $(RESULTS_DIR)/analysis

# ── Derived flags ─────────────────────────────────────────────────────────
RUN_FLAGS := --trials $(TRIALS) --strategy $(STRATEGY) --timeout $(TIMEOUT) --seed $(SEED) --provider $(PROVIDER)
ifdef MODELS
  RUN_FLAGS += --models $(MODELS)
endif
ifdef PROBLEMS
  RUN_FLAGS += --problems $(PROBLEMS)
endif
ifdef SKIP_RENDER
  RUN_FLAGS += --skip-render
endif
ifdef BASE_URL
  RUN_FLAGS += --base-url $(BASE_URL)
endif
ifdef API_KEY
  RUN_FLAGS += --api-key $(API_KEY)
endif

# ══════════════════════════════════════════════════════════════════════════
#  SETUP
# ══════════════════════════════════════════════════════════════════════════

.PHONY: help setup venv install env check-env check-key check-manim

## Show this help message
help:
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════════╗"
	@echo "║              ManiBench — Available Commands                     ║"
	@echo "╚══════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "  SETUP"
	@echo "  ─────────────────────────────────────────────────────────────"
	@echo "  make setup          Create venv, install deps, copy .env"
	@echo "  make venv           Create Python virtual environment only"
	@echo "  make install        Install requirements into venv"
	@echo "  make env            Copy .env.example → .env (won't overwrite)"
	@echo "  make check-env      Verify venv, deps, API key, Manim"
	@echo ""
	@echo "  EVALUATION"
	@echo "  ─────────────────────────────────────────────────────────────"
	@echo "  make run            Full evaluation (all models × problems × 3 trials)"
	@echo "  make quick-test     Smoke test: GPT-4o, MB-005, 1 trial, skip-render"
	@echo "  make run-single     One model, one problem  (set MODELS= PROBLEMS=)"
	@echo "  make run-fast       All models, skip rendering (static analysis only)"
	@echo "  make run-cot        Full run with chain-of-thought strategy"
	@echo "  make run-all-strategies  Run all 5 prompt strategies sequentially"
	@echo ""
	@echo "  INFERENCE.NET"
	@echo "  ───────────────────────────────────────────────────────────"
	@echo "  make run-inference             Full eval via Inference.net"
	@echo "  make inference-quick-test      Smoke test via Inference.net"
	@echo "  make inference-run-cot         Full CoT run via Inference.net"
	@echo "  make inference-run-all-strategies  All 5 strategies via Inference.net"
	@echo "  make inference-list-models     List Inference.net models"
	@echo "  make run PROVIDER=inference    Use Inference.net with any target"
	@echo ""
	@echo "  OPENAI-COMPATIBLE / vLLM"
	@echo "  ───────────────────────────────────────────────────────────"
	@echo "  make run-openai                Eval via OpenAI-compatible endpoint"
	@echo "  make openai-quick-test         Smoke test via OpenAI-compatible API"
	@echo "  make openai-list-models        List models from OPENAI_BASE_URL"
	@echo "  make run PROVIDER=openai BASE_URL=http://localhost:8000/v1 MODELS=..."
	@echo ""
	@echo "  ANALYSIS"
	@echo "  ─────────────────────────────────────────────────────────────"
	@echo "  make analyze        Generate tables from latest results file"
	@echo "  make analyze-all    Merge & analyze ALL results in results/"
	@echo "  make list-results   Show available results files"
	@echo ""
	@echo "  UTILITIES"
	@echo "  ─────────────────────────────────────────────────────────────"
	@echo "  make validate       Validate dataset JSON + evaluation code"
	@echo "  make render-sample  Render a sample Manim scene to test setup"
	@echo "  make list-models    Query OpenRouter for available models"
	@echo "  make count-raw      Count lines in raw_code/ reference files"
	@echo ""
	@echo "  CLEANUP"
	@echo "  ─────────────────────────────────────────────────────────────"
	@echo "  make clean          Remove generated code, logs, __pycache__"
	@echo "  make clean-results  Remove results + analysis (keeps code & logs)"
	@echo "  make clean-all      Remove everything: venv + results + generated"
	@echo "  make clean-media    Remove Manim media/ output directory"
	@echo ""
	@echo "  VARIABLES (override on CLI)"
	@echo "  ─────────────────────────────────────────────────────────────"
	@echo "  TRIALS=3            Trials per (model, problem) pair"
	@echo "  STRATEGY=zero_shot  Prompt strategy"
	@echo "  TIMEOUT=60          Manim render timeout (seconds)"
	@echo "  MODELS=\"gpt-4o\"     Space-separated model short names"
	@echo "  PROBLEMS=\"MB-001\"   Space-separated problem IDs"
	@echo "  SKIP_RENDER=1       Set to skip Manim rendering"
	@echo "  PROVIDER=openrouter API provider: openrouter | inference | openai"
	@echo "  BASE_URL=           OpenAI-compatible / OpenRouter base URL override"
	@echo "  API_KEY=            API token (overrides .env / env var)"
	@echo ""
	@echo "  Examples:"
	@echo "    make run TRIALS=1 MODELS=\"gpt-4o claude-sonnet-4\""
	@echo "    make run API_KEY=sk-or-v1-... MODELS=\"claude-sonnet-4\" TRIALS=1"
	@echo "    make run PROBLEMS=\"MB-001 MB-002 MB-005\" STRATEGY=cot"
	@echo "  make run-single MODELS=deepseek-r1 PROBLEMS=MB-003"
	@echo "    make run PROVIDER=inference MODELS=\"Llama-3.3-70B\""
	@echo "    make run PROVIDER=openai BASE_URL=http://localhost:8000/v1 MODELS=\"Qwen/Qwen2.5-7B-Instruct\""
	@echo ""

## Full one-time setup: venv + dependencies + .env
setup: venv install env
	@echo ""
	@echo "✅  Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env and add your OpenRouter API key"
	@echo "  2. Activate the venv:  source $(VENV)/bin/activate"
	@echo "  3. Smoke test:         make quick-test"
	@echo "  4. Full run:           make run"
	@echo ""

## Create Python virtual environment
venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment in $(VENV)/ ..."; \
		$(PYTHON) -m venv $(VENV); \
		echo "✓ venv created"; \
	else \
		echo "✓ venv already exists"; \
	fi

## Install Python dependencies into venv
install: venv
	@echo "Installing dependencies ..."
	$(PIP) install --upgrade pip -q
	$(PIP) install -r requirements.txt -q
	@echo "✓ Dependencies installed"

## Copy .env.example → .env (will NOT overwrite existing .env)
env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env from .env.example — edit it now!"; \
	else \
		echo "✓ .env already exists (not overwritten)"; \
	fi

## Verify environment: venv, deps, API key, Manim installation
check-env: check-key check-manim
	@echo ""
	@echo "Checking Python & dependencies ..."
	@$(PY) -c "import requests; print('  ✓ requests', requests.__version__)"
	@$(PY) -c "import tabulate; print('  ✓ tabulate', tabulate.__version__)"
	@$(PY) -c "import dotenv; print('  ✓ python-dotenv OK')" 2>/dev/null || echo "  ⚠ python-dotenv not found (optional)"
	@$(PY) -c "import tqdm; print('  ✓ tqdm', tqdm.__version__)" 2>/dev/null || echo "  ⚠ tqdm not found (optional)"
	@echo ""
	@echo "Checking evaluation package ..."
	@$(PY) -c "from evaluation.config import DEFAULT_MODELS; print('  ✓ evaluation.config — %d models' % len(DEFAULT_MODELS))"
	@$(PY) -c "from evaluation.metrics import compute_executability; print('  ✓ evaluation.metrics OK')"
	@$(PY) -c "from evaluation.prompts import get_strategy_names; print('  ✓ evaluation.prompts —', get_strategy_names())"
	@echo ""
	@echo "✅  Environment looks good!"

check-key:
	@echo "Checking API keys ..."
	@if [ -f .env ]; then \
		source .env 2>/dev/null; \
	fi; \
	if [ -z "$$OPENROUTER_API_KEY" ]; then \
		echo "  ⚠  OPENROUTER_API_KEY not set."; \
		echo "     → Edit .env, export OPENROUTER_API_KEY='sk-or-v1-...', or pass --api-key / API_KEY="; \
	else \
		echo "  ✓ OPENROUTER_API_KEY is set ($${OPENROUTER_API_KEY:0:12}...)"; \
	fi; \
	if [ -z "$$INFERENCE_API_KEY" ]; then \
		echo "  ⚠  INFERENCE_API_KEY not set (needed only for --provider inference)."; \
		echo "     → Edit .env or: export INFERENCE_API_KEY='your-key'"; \
	else \
		echo "  ✓ INFERENCE_API_KEY is set ($${INFERENCE_API_KEY:0:12}...)"; \
	fi

check-manim:
	@echo "Checking Manim CE ..."
	@$(PY) -c "import manim; print('  ✓ Manim CE', manim.__version__)" 2>/dev/null || \
		echo "  ⚠ Manim CE not importable — run: make install"


# ══════════════════════════════════════════════════════════════════════════
#  EVALUATION
# ══════════════════════════════════════════════════════════════════════════

.PHONY: run quick-test run-single run-fast run-cot run-all-strategies

## Full evaluation run (6 models × 12 problems × 3 trials = 216 API calls)
run:
	@echo "════════════════════════════════════════════════════════"
	@echo "  ManiBench Full Evaluation"
	@echo "  Strategy: $(STRATEGY) | Trials: $(TRIALS)"
	@echo "════════════════════════════════════════════════════════"
	$(PY) -m evaluation.run $(RUN_FLAGS)

## Smoke test: 1 model (GPT-4o), 1 easy problem (MB-005), 1 trial, no render
quick-test:
	@echo "════════════════════════════════════════════════════════"
	@echo "  ManiBench Quick Smoke Test"
	@echo "════════════════════════════════════════════════════════"
	$(PY) -m evaluation.run \
		--models GPT-4o \
		--problems MB-005 \
		--trials 1 \
		--skip-render

## Run a specific model × problem combo (set MODELS and PROBLEMS vars)
run-single:
ifndef MODELS
	$(error Set MODELS, e.g.: make run-single MODELS=gpt-4o PROBLEMS=MB-001)
endif
ifndef PROBLEMS
	$(error Set PROBLEMS, e.g.: make run-single MODELS=gpt-4o PROBLEMS=MB-001)
endif
	$(PY) -m evaluation.run $(RUN_FLAGS)

## All models, all problems, skip Manim rendering (fast static analysis)
run-fast:
	$(PY) -m evaluation.run --trials $(TRIALS) --strategy $(STRATEGY) --skip-render

## Full run with chain-of-thought prompting
run-cot:
	$(PY) -m evaluation.run --trials $(TRIALS) --strategy cot

## Run all 5 prompt strategies back-to-back (5 × 216 = 1,080 calls)
run-all-strategies:
	@echo "Running all prompt strategies sequentially ..."
	@for strat in zero_shot few_shot cot constraint version_aware; do \
		echo ""; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo "  Strategy: $$strat"; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		$(PY) -m evaluation.run --trials $(TRIALS) --strategy $$strat; \
	done
	@echo ""
	@echo "✅  All strategies complete. Run 'make analyze-all' for combined report."


# ── Inference.net targets ─────────────────────────────────────────────────

.PHONY: run-inference inference-quick-test inference-list-models inference-run-cot inference-run-all-strategies

## Full evaluation via Inference.net (all inference models × all problems)
run-inference:
	@echo "════════════════════════════════════════════════════════"
	@echo "  ManiBench Evaluation — Inference.net"
	@echo "  Strategy: $(STRATEGY) | Trials: $(TRIALS)"
	@echo "════════════════════════════════════════════════════════"
	$(PY) -m evaluation.run --provider inference --trials $(TRIALS) --strategy $(STRATEGY) --timeout $(TIMEOUT)

## Smoke test via Inference.net: 1 model, 1 problem, 1 trial, skip render
inference-quick-test:
	@echo "════════════════════════════════════════════════════════"
	@echo "  ManiBench Quick Test — Inference.net"
	@echo "════════════════════════════════════════════════════════"
	$(PY) -m evaluation.run \
		--provider inference \
		--models Gemma-3-27B \
		--problems MB-005 \
		--trials 1 \
		--skip-render

## List models available on Inference.net
inference-list-models:
	@$(PY) -c "$$INFERENCE_LIST_MODELS_SCRIPT"

define INFERENCE_LIST_MODELS_SCRIPT
from evaluation.inference_client import InferenceNetClient
client = InferenceNetClient()
models = client.list_models()
print(f"Inference.net has {len(models)} models available.\n")
from evaluation.config import INFERENCE_MODELS
print("ManiBench configured Inference.net models:")
for m in INFERENCE_MODELS:
    match = [x for x in models if x.get("id") == m.id]
    status = "✓ available" if match else "✗ not found"
    print(f"  {m.short_name:<22} {m.id:<50} {status}")
endef
export INFERENCE_LIST_MODELS_SCRIPT

## Full run with chain-of-thought strategy via Inference.net
inference-run-cot:
	@echo "════════════════════════════════════════════════════════"
	@echo "  ManiBench CoT Evaluation — Inference.net"
	@echo "  Strategy: cot | Trials: $(TRIALS)"
	@echo "════════════════════════════════════════════════════════"
	$(PY) -m evaluation.run --provider inference --trials $(TRIALS) --strategy cot --timeout $(TIMEOUT)

## Run all 5 prompt strategies sequentially via Inference.net (5 × inference runs)
inference-run-all-strategies:
	@echo "Running all prompt strategies via Inference.net ..."
	@for strat in zero_shot few_shot cot constraint version_aware; do \
		echo ""; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo "  Strategy: $$strat  [Inference.net]"; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		$(PY) -m evaluation.run --provider inference --trials $(TRIALS) --strategy $$strat --timeout $(TIMEOUT); \
	done
	@echo ""
	@echo "✅  All Inference.net strategies complete. Run 'make analyze-all' for combined report."


# ── OpenAI-compatible / vLLM targets ──────────────────────────────────────

.PHONY: run-openai openai-quick-test openai-list-models

## Evaluation via OpenAI-compatible endpoint (requires BASE_URL + MODELS)
run-openai:
	@if [ -z "$(BASE_URL)" ] && [ -z "$$OPENAI_BASE_URL" ]; then \
		echo "ERROR: set BASE_URL=http://host:port/v1 or OPENAI_BASE_URL in .env"; \
		exit 1; \
	fi
	@if [ -z "$(MODELS)" ]; then \
		echo "ERROR: set MODELS to the served model id(s)"; \
		echo "  Example: make run-openai BASE_URL=http://localhost:8000/v1 MODELS=\"Qwen/Qwen2.5-7B-Instruct\""; \
		exit 1; \
	fi
	@echo "════════════════════════════════════════════════════════"
	@echo "  ManiBench Evaluation — OpenAI-compatible / vLLM"
	@echo "  Base URL: $(or $(BASE_URL),$${OPENAI_BASE_URL})"
	@echo "  Models:   $(MODELS)"
	@echo "  Strategy: $(STRATEGY) | Trials: $(TRIALS)"
	@echo "════════════════════════════════════════════════════════"
	$(PY) -m evaluation.run --provider openai \
		$(if $(BASE_URL),--base-url $(BASE_URL),) \
		--models $(MODELS) \
		$(if $(PROBLEMS),--problems $(PROBLEMS),) \
		--trials $(TRIALS) --strategy $(STRATEGY) --timeout $(TIMEOUT) --seed $(SEED) \
		$(if $(SKIP_RENDER),--skip-render,)

## Smoke test via OpenAI-compatible API (1 problem, 1 trial, skip render)
openai-quick-test:
	@if [ -z "$(BASE_URL)" ] && [ -z "$$OPENAI_BASE_URL" ]; then \
		echo "ERROR: set BASE_URL=http://host:port/v1 or OPENAI_BASE_URL in .env"; \
		exit 1; \
	fi
	@if [ -z "$(MODELS)" ]; then \
		echo "ERROR: set MODELS to the served model id"; \
		exit 1; \
	fi
	@echo "════════════════════════════════════════════════════════"
	@echo "  ManiBench Quick Test — OpenAI-compatible / vLLM"
	@echo "════════════════════════════════════════════════════════"
	$(PY) -m evaluation.run \
		--provider openai \
		$(if $(BASE_URL),--base-url $(BASE_URL),) \
		--models $(MODELS) \
		--problems $(or $(PROBLEMS),MB-005) \
		--trials 1 \
		--skip-render

## List models from an OpenAI-compatible /models endpoint
openai-list-models:
	@BASE_URL="$(BASE_URL)" $(PY) -c "$$OPENAI_LIST_MODELS_SCRIPT"

define OPENAI_LIST_MODELS_SCRIPT
import os
from evaluation.openai_client import OpenAICompatibleClient
from evaluation.config import OPENAI_BASE_URL
base = os.environ.get("BASE_URL") or OPENAI_BASE_URL
if not base:
    raise SystemExit("Set OPENAI_BASE_URL in .env or: make openai-list-models BASE_URL=http://localhost:8000/v1")
client = OpenAICompatibleClient(base_url=base)
models = client.list_models()
print(f"Found {len(models)} model(s) at {base}:\n")
for m in models:
    print(f"  {m.get('id', m)}")
endef
export OPENAI_LIST_MODELS_SCRIPT


# ══════════════════════════════════════════════════════════════════════════
#  ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

.PHONY: analyze analyze-all list-results

## Analyze the most recent results file → LaTeX + CSV + Markdown
analyze:
	@LATEST=$$(ls -t $(RESULTS_DIR)/results_*.json 2>/dev/null | head -1); \
	if [ -z "$$LATEST" ]; then \
		echo "ERROR: No results found in $(RESULTS_DIR)/"; \
		echo "  → Run 'make run' or 'make quick-test' first."; \
		exit 1; \
	fi; \
	echo "Analyzing: $$LATEST"; \
	$(PY) -m evaluation.analysis --results "$$LATEST"

## Merge and analyze ALL results files in results/
analyze-all:
	@if [ -z "$$(ls $(RESULTS_DIR)/results_*.json 2>/dev/null)" ]; then \
		echo "ERROR: No results found in $(RESULTS_DIR)/"; \
		exit 1; \
	fi
	$(PY) -m evaluation.analysis --results-dir $(RESULTS_DIR)

## List available results files with sizes and dates
list-results:
	@echo "Results files:"
	@ls -lh $(RESULTS_DIR)/results_*.json 2>/dev/null || echo "  (none)"
	@echo ""
	@echo "Log files:"
	@ls -lh $(LOGS_DIR)/run_*.jsonl 2>/dev/null || echo "  (none)"
	@echo ""
	@echo "Summaries:"
	@ls -lh $(LOGS_DIR)/*_summary.json 2>/dev/null || echo "  (none)"
	@echo ""
	@echo "Analysis outputs:"
	@ls -lh $(ANALYSIS_DIR)/ 2>/dev/null || echo "  (none)"


# ══════════════════════════════════════════════════════════════════════════
#  UTILITIES
# ══════════════════════════════════════════════════════════════════════════

.PHONY: validate render-sample list-models count-raw dataset-info

## Validate dataset JSON schema and evaluation package imports
validate:
	@echo "Validating dataset ..."
	@$(PY) -c "$$VALIDATE_SCRIPT"
	@echo ""
	@echo "Validating evaluation package ..."
	@$(PY) -c "from evaluation.run import main; print('  ✓ evaluation.run OK')"
	@$(PY) -c "from evaluation.analysis import main; print('  ✓ evaluation.analysis OK')"
	@$(PY) -c "from evaluation.openrouter_client import OpenRouterClient; print('  ✓ openrouter_client OK')"
	@echo ""
	@echo "✅  Validation passed"

define VALIDATE_SCRIPT
import json, sys
data = json.load(open('ManiBench_Pilot_Dataset.json'))
problems = data.get('problems', [])
print(f'  ✓ Dataset loaded: {len(problems)} problems')
ids = [p['id'] for p in problems]
print(f'  ✓ IDs: {ids}')
for p in problems:
    assert 'full_prompt' in p, f"Missing full_prompt in {p['id']}"
    assert 'required_visual_events' in p, f"Missing events in {p['id']}"
    n_events = len(p['required_visual_events'])
    print(f"    {p['id']}: {p.get('difficulty','?')}★  {n_events} events  {p.get('category','')}")
print('  ✓ All problems validated')
endef
export VALIDATE_SCRIPT

## Render a minimal Manim scene to verify Manim CE installation
render-sample:
	@echo "Rendering a test Manim scene ..."
	@$(PY) -c "$$RENDER_SAMPLE_SCRIPT"

define RENDER_SAMPLE_SCRIPT
from manim import *
class TestScene(Scene):
    def construct(self):
        t = Text("ManiBench Test", font_size=48)
        self.play(Write(t))
        self.wait(0.5)
config.media_dir = "media"
scene = TestScene()
scene.render()
print("✓ Manim rendering works! Check media/ for output.")
endef
export RENDER_SAMPLE_SCRIPT

## Query OpenRouter for available models (requires API key)
list-models:
	@$(PY) -c "$$LIST_MODELS_SCRIPT"

define LIST_MODELS_SCRIPT
from evaluation.openrouter_client import OpenRouterClient
client = OpenRouterClient()
models = client.list_models()
print(f"OpenRouter has {len(models)} models available.\n")
from evaluation.config import DEFAULT_MODELS
print("ManiBench configured models:")
for m in DEFAULT_MODELS:
    match = [x for x in models if x.get("id") == m.id]
    status = "✓ available" if match else "✗ not found"
    print(f"  {m.short_name:<22} {m.id:<45} {status}")
endef
export LIST_MODELS_SCRIPT

## Count lines of code in raw_code/ reference files
count-raw:
	@echo "Raw code reference files (3Blue1Brown ManimGL source):"
	@echo "──────────────────────────────────────────────────────"
	@total=0; \
	for dir in raw_code/*/; do \
		name=$$(basename $$dir); \
		lines=$$(find $$dir -name '*.py' -exec cat {} + 2>/dev/null | wc -l); \
		files=$$(find $$dir -name '*.py' 2>/dev/null | wc -l); \
		printf "  %-25s %3d files  %6d lines\n" "$$name/" "$$files" "$$lines"; \
		total=$$((total + lines)); \
	done; \
	echo "──────────────────────────────────────────────────────"; \
	printf "  %-25s           %6d lines\n" "TOTAL" "$$total"

## Print dataset summary (problems, difficulty distribution, domains)
dataset-info:
	@$(PY) -c "$$DATASET_INFO_SCRIPT"

define DATASET_INFO_SCRIPT
import json
from collections import Counter
data = json.load(open('ManiBench_Pilot_Dataset.json'))
ps = data['problems']
print(f"ManiBench Pilot Dataset — {len(ps)} problems")
print(f"Schema: {data.get('schema_version', '?')}, Version: {data.get('version', '?')}")
print()
print(f"{'ID':<8} {'Lvl':>3}  {'Category':<30} {'Domain':<25} Title")
print("─" * 95)
for p in ps:
    cat = p.get('category', '')
    if isinstance(cat, list):
        cat = ', '.join(cat)
    dom = p.get('domain', '')
    if isinstance(dom, list):
        dom = ', '.join(dom)
    diff = p.get('difficulty', p.get('difficulty_level', '?'))
    print(f"{p['id']:<8} {str(diff):>3}  {cat:<30} {dom:<25} {p['title']}")
print()
diffs = Counter(p.get('difficulty', p.get('difficulty_level')) for p in ps)
print("Difficulty distribution:", dict(sorted(diffs.items())))
cats = Counter()
for p in ps:
    c = p.get('category', '')
    if isinstance(c, list):
        for x in c:
            cats[x.strip()] += 1
    else:
        for x in c.split(','):
            cats[x.strip()] += 1
print("Categories:", dict(cats))
endef
export DATASET_INFO_SCRIPT


# ══════════════════════════════════════════════════════════════════════════
#  CLEANUP
# ══════════════════════════════════════════════════════════════════════════

.PHONY: clean clean-results clean-all clean-media

## Remove generated code, logs, and __pycache__ (keeps results)
clean:
	@echo "Cleaning generated code and caches ..."
	rm -rf $(GEN_CODE_DIR)/*
	rm -rf $(LOGS_DIR)/*.jsonl $(LOGS_DIR)/*_summary.json
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cleaned"

## Remove results and analysis outputs
clean-results:
	@echo "Removing results and analysis ..."
	rm -rf $(RESULTS_DIR)/*.json
	rm -rf $(ANALYSIS_DIR)
	@echo "✓ Results cleaned"

## Remove Manim media/ output directory
clean-media:
	@echo "Removing Manim media output ..."
	rm -rf media/
	@echo "✓ Media cleaned"

## Nuclear option: remove venv + all generated artifacts
clean-all: clean clean-results clean-media
	@echo "Removing virtual environment ..."
	rm -rf $(VENV)
	@echo "✓ Everything cleaned (run 'make setup' to start fresh)"
