# prompt_optimization

Prompts for every IR layer plus tools to score and evolve them.

---

## What's in here

```
prompts/          system prompts for each generation stage
datasets/         labeled examples (train / dev / test)
dspy/             DSPy signatures, programs, and metrics
gepa/             evolutionary prompt optimizer
reports/          output from optimization runs
```

---

## How to run

### 1 — Basic agent (classification only)

From the repo root:

```bash
uv run --package agents python apps/agents/main.py
```

Takes a hardcoded request, prints a `Classification` with `subject` and `topic`.

---

### 2 — GEPA: optimize the classifier prompt

Uses [`dspy.GEPA`](https://dspy.ai/api/optimizers/GEPA/) — the real reflective
Genetic-Pareto optimizer from [Agrawal et al., 2025](https://arxiv.org/abs/2507.19457),
not a hand-rolled mutate-and-score loop.

```bash
uv run --package agents python -m apps.agents.prompt_optimization.gepa.optimize_classifier
```

What it does:
- Loads `datasets/train.jsonl` (15 examples) for reflective updates and
  `datasets/dev.jsonl` (8 examples) for Pareto-tracked validation
- Wraps `ClassifierProgram` (`dspy/programs.py`) seeded with the instruction
  in `prompts/classification.py`
- Scores every rollout with `classification_metric` in `gepa/optimize_classifier.py`,
  which returns both a score *and* natural-language feedback (e.g. "Wrong subject:
  predicted 'math', expected 'ai' — re-check the domain guide")
- GEPA's `reflection_lm` reads that feedback plus the execution trace and proposes
  a new instruction for the predictor; the Pareto frontier of candidates is
  tracked across rounds until the budget (`auto="light"` by default) is exhausted
- Saves the optimized instructions to `reports/classifier_optimized_predict.txt`

Tune it by passing a custom `GEPAConfig` (see `gepa/config.py` for every field —
budget, reflection/task models, candidate selection strategy, merge, etc.):

```python
from apps.agents.prompt_optimization.gepa.config import GEPAConfig
from apps.agents.prompt_optimization.gepa.optimize_classifier import run_optimization

run_optimization(GEPAConfig(auto="medium", reflection_model="openrouter/openai/gpt-4o-mini"))
```

`reflection_model` benefits from being a strong model (GEPA's own docs
recommend something like GPT-5-class reasoning) even if `task_model` — the
model actually being optimized — stays cheap.

---

### 3 — Other DSPy optimizers

`dspy` is already a dependency (used by GEPA above). Any other DSPy optimizer
(e.g. `BootstrapFewShot`) can be wired up the same way against a program in
`dspy/programs.py` and a metric in `dspy/metrics.py`:

```python
import dspy
from apps.agents.prompt_optimization.dspy.programs import ClassifierProgram
from apps.agents.prompt_optimization.dspy.metrics import classification_score

dspy.configure(lm=dspy.LM("openrouter/openrouter/free"))

optimizer = dspy.BootstrapFewShot(metric=classification_score)
compiled = optimizer.compile(ClassifierProgram(), trainset=your_trainset)
```

---

## Where outputs go

| What | Where |
|---|---|
| Best instruction from GEPA (one file per predictor) | `reports/classifier_optimized_<predictor>.txt` |
| Optimization run notes | `reports/classifier_v1.md`, `classifier_v2.md` |
| Full GEPA logs / checkpoints (if `log_dir` set in `GEPAConfig`) | `<log_dir>/` |
| Validation scores | printed to stdout during the run |

---

## Dev notes

**Adding a new prompt**
1. Create `prompts/<stage>.py` with a `<stage>_instruction` string.
2. Export it from `prompts/__init__.py`.
3. Add a DSPy `Signature` in `dspy/signatures.py` and a metric in `dspy/metrics.py`.

**Prompt covers the IR invariants**
Each prompt repeats the hard limits the Pydantic IR validator enforces (≤3 objects/beat, frame-safe positions, CREATE before use, etc.). This lets the LLM pre-validate before the IR does, cutting silent failures.

**Dataset format**
Each `.jsonl` line is a JSON object with at minimum `"input"` and `"subject"`. Add more fields as the task grows:
```json
{"input": "explain gradient descent", "subject": "ai", "topic": "Gradient Descent"}
```

**Models**
The default model is `openrouter/openrouter/free` for both the task and reflection LM. Swap them via `GEPAConfig.task_model` / `reflection_model`, and set `OPENROUTER_API_KEY` in `.env`.
