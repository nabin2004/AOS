---
language:
- en
license: mit
tags:
- benchmark
- manim
- code-generation
- llm-evaluation
- animation
- mathematics
- visual-logic
pretty_name: ManiBench
size_categories:
- n<1K
---

# ManiBench: A Benchmark for Testing Visual-Logic Drift and Syntactic Hallucinations in Manim Code Generation

## Overview

**ManiBench** is a specialized benchmark dataset for evaluating Large Language Model (LLM) performance in generating Manim CE (Community Edition) code—mathematical animations used for educational content creation.

This benchmark addresses two critical failure modes in LLM-generated code:

1. **Syntactic Hallucinations**: Code that appears valid in Python but references non-existent Manim functions, uses deprecated APIs, or breaks under specific library versions.

2. **Visual-Logic Drift**: Code that executes without errors but produces incorrect, incomplete, or misaligned animations that fail to communicate the intended mathematical concept.

---

## Files in This Package

### Core Research Documents

1. **ManiBench_Specification.md** (~36 KB)
   - Full research paper with abstract, introduction, and problem definitions
   - Complete description of 12 pilot problems with video sources
   - Metric definitions (Executability, Version-Conflict Rate, Alignment, Coverage)
   - Preliminary evaluation results
   - Reference code analysis methodology
   - **Start here for comprehensive understanding**

2. **ManiBench_Pilot_Dataset.json** (~151 KB)
   - Structured JSON dataset (schema v2.0) with 12 curated pilot problems
   - Each problem includes: video source, category, difficulty level, full prompt, required visual events, coverage requirements, success criteria, common failure modes, pedagogical intent
   - **Reference code analysis** for all 12 problems: scene class inventories, visual technique catalogs, Manim API patterns, and detailed ManimGL→ManimCE version conflict notes — derived from 3Blue1Brown's original source code
   - Raw code collection status and file paths for all 12 problems
   - Machine-readable format for programmatic access
   - **Use this to generate prompts for LLMs**

3. **ManiBench_Evaluation_Rubric.md** (13 KB)
   - Detailed scoring methodology for all four metrics
   - Worked examples showing how to compute Alignment and Coverage scores
   - Rubric for human evaluators with disagreement resolution procedures
   - Special cases and edge cases
   - **Reference while scoring animations**

### Practical Guides

4. **ManiBench_QuickStart.md**
   - Step-by-step workflow for evaluating LLM code
   - Difficulty progression recommendations
   - Common failure patterns observed in early results
   - FAQ and troubleshooting
   - **Read this if you're evaluating code for the first time**

5. **ManiBench_Prompt_Engineering_Guide.md**
   - Strategies for prompting LLMs to generate high-quality Manim code
   - Zero-shot, few-shot, chain-of-thought, and constraint-based approaches
   - Solutions to common failure cases
   - Prompt templates by problem difficulty
   - **Use this to improve LLM code quality**

6. **README.md** (this file)
   - Overview and file guide
   - Citation information
   - Links and resources

### Automated Evaluation Framework

7. **evaluation/** (Python package)
   - Full automated evaluation pipeline using OpenRouter API
   - Supports 6 LLM models out of the box (GPT-4o, Claude Sonnet 4, Gemini 2.5 Pro, DeepSeek-R1, Llama 4 Maverick, Qwen 2.5 Coder)
   - 5 prompt strategies (zero-shot, few-shot, chain-of-thought, constraint, version-aware)
   - 4 automated metrics with structured JSONL logging
   - Paper-ready LaTeX table and Markdown report generation
   - **Use this to reproduce evaluation results**

   Key modules:
   - `evaluation/run.py` — Main CLI runner
   - `evaluation/config.py` — Models, paths, GL detection patterns
   - `evaluation/openrouter_client.py` — OpenRouter API client with retries
   - `evaluation/openai_client.py` — OpenAI-compatible / vLLM client
   - `evaluation/prompts.py` — 5 prompt strategy builders

   - `evaluation/metrics/` — Executability, Version-Conflict, Alignment, Coverage
   - `evaluation/analysis.py` — LaTeX/CSV/Markdown report generator
   - `evaluation/logger.py` — Structured experiment logging

8. **requirements.txt** — Python dependencies for the evaluation framework
9. **.env.example** — Template for API key configuration
10. **Makefile** — All project commands (`make help` to see them all)
11. **DEVELOPMENT.md** — Full developer guide: setup, pipeline architecture, workflows, troubleshooting

### Raw Code Reference

7. **raw_code/** (directory)
   - Original 3Blue1Brown source code for all 12 benchmark problems
   - Organized by problem: `colliding_blocks_v2/`, `nn/`, `convolutions/`, `eigen/`, `determinant/`, `clt/`, `med_test/`, `chain_rule/`, `ftc/`, `taylor_series/`, `hairy_ball/`, `windmill/`
   - Total: ~53,000 lines of ManimGL code across 21 source files
   - **For reference only** — not shared with LLMs during evaluation

---

## HuggingFace Dataset

ManiBench is hosted on HuggingFace Datasets:

🤗 **[nabin2004/ManiBench](https://huggingface.co/datasets/nabin2004/ManiBench)**

```python
# Load via HuggingFace
from datasets import load_dataset
ds = load_dataset("nabin2004/ManiBench")
```

---

## Benchmark Scope

### 12 Pilot Problems

The benchmark launches with 12 hand-curated problems drawn from 3Blue1Brown's published videos:

| ID | Title | Domain | Level | Category |
|----|-------|--------|-------|----------|
| MB-001 | Colliding Blocks Compute π | Physics | 4 | Multi-scene |
| MB-002 | Gradient Descent, How Neural Networks Learn | ML/Calculus | 3 | Drift-sensitive |
| MB-003 | But What Is a Convolution? | Signal Processing | 3 | Drift-sensitive |
| MB-004 | Eigenvectors & Eigenvalues | Linear Algebra | 4 | Direct visualization |
| MB-005 | The Determinant | Linear Algebra | 2 | Direct visualization |
| MB-006 | The Central Limit Theorem | Probability | 3 | Drift-sensitive |
| MB-007 | The Medical Test Paradox (Bayes' Theorem) | Probability | 2 | Direct visualization |
| MB-008 | Visualizing the Chain Rule | Calculus | 3 | Direct visualization |
| MB-009 | Integration and the Fundamental Theorem | Calculus | 3 | Direct visualization |
| MB-010 | Taylor Series | Calculus | 4 | Direct visualization |
| MB-011 | The Hairy Ball Theorem | Topology | 5 | Multi-scene |
| MB-012 | The Windmill Problem | Geometry | 4 | Drift-sensitive |

### Metrics

Each submission is evaluated on four metrics:

1. **Executability (Pass@1)**: Binary. Does code run without exceptions or deprecated imports?
2. **Version-Conflict Error Rate**: Percentage of runs triggering version-specific errors
3. **Alignment Score (0.0–1.0)**: Weighted fraction of required visual events present and correctly timed
4. **Coverage Score (0.0–1.0)**: Density of pedagogical elements (labels, formulas, numeric evidence)

### Reference Code Analysis

All 12 problems include `reference_code_analysis` derived from 3Blue1Brown's original ManimGL source code:

| ID | Source Lines | Scene Classes | Visual Techniques | GL→CE Conflicts |
|----|-------------|---------------|-------------------|------------------|
| MB-001 | 2,193 | 16 | 10 | 15 |
| MB-002 | 8,598 | 16 | 16 | 13 |
| MB-003 | 3,309 | 13 | 11 | 14 |
| MB-004 | 5,120 | 13 | 9 | 10 |
| MB-005 | 1,132 | 11 | 7 | 10 |
| MB-006 | 7,036 | 12 | 9 | 11 |
| MB-007 | 7,044 | 13 | 9 | 11 |
| MB-008 | 2,287 | 4 | 7 | 10 |
| MB-009 | 4,943 | 11 | 9 | 11 |
| MB-010 | 3,676 | 11 | 9 | 10 |
| MB-011 | 3,796 | 12 | 12 | 16 |
| MB-012 | 4,135 | 11 | 12 | 14 |

Each analysis includes:
- **Scene class inventory** with descriptions and key methods
- **Visual technique catalog** (e.g., Riemann rectangles, grid transformations, particle systems)
- **Manim API patterns** (updaters, animation types, 3D constructs, custom classes)
- **Version conflict notes** mapping ManimGL constructs to ManimCE equivalents

---

## Quick Start

### Automated Evaluation (Recommended)

Run the full benchmark evaluation programmatically using the `evaluation/` framework.
See **[DEVELOPMENT.md](DEVELOPMENT.md)** for the full developer guide.

#### Using Make (Recommended)

```bash
# 1. One-command setup: venv + deps + .env
make setup

# 2. Add your API key
nano .env   # set OPENROUTER_API_KEY=sk-or-v1-...

# 3. Activate venv
source .venv/bin/activate

# 4. Smoke test (1 API call, no rendering)
make quick-test

# 5. Full evaluation (6 models × 12 problems × 3 trials)
make run

# 6. Chain-of-thought strategy
make run STRATEGY=cot

# 7. Specific models and problems
make run MODELS="gpt-4o claude-sonnet-4" PROBLEMS="MB-001 MB-005" TRIALS=1

# 8. Skip Manim rendering (static analysis only — faster)
make run-fast

# 9. Generate paper tables from results
make analyze

# 10. See all available commands
make help
```

#### Using Python Directly

```bash
# 1. Clone/download the repository
git clone https://huggingface.co/datasets/nabin2004/ManiBench
cd ManiBench

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your OpenRouter API token (or pass --api-key on each run)
export OPENROUTER_API_KEY='sk-or-v1-your-key-here'

# 4. Run evaluation (all models × all problems × 3 trials)
python -m evaluation.run

# 5. Quick test (single model, single problem, 1 trial)
python -m evaluation.run --models gpt-4o --problems MB-005 --trials 1

#    Or pass the OpenRouter token on the CLI instead of env:
python -m evaluation.run --api-key sk-or-v1-... --models claude-sonnet-4 --trials 1

# 6. Use a specific prompt strategy
python -m evaluation.run --strategy cot --models claude-sonnet-4

# 7. Skip Manim rendering (static analysis only — faster)
python -m evaluation.run --skip-render

# 8. OpenAI-compatible / vLLM endpoint (any served model id)
python -m evaluation.run --provider openai \
  --base-url http://localhost:8000/v1 \
  --models Qwen/Qwen2.5-Coder-7B-Instruct \
  --problems MB-001 --trials 1

# 9. Generate paper tables from results
python -m evaluation.analysis --results results/results_<run_id>.json
```

#### Available Models

| Short Name | OpenRouter Model ID | Provider |
|-----------|---------------------|----------|
| `gpt-4o` | `openai/gpt-4o-2024-11-20` | OpenAI |
| `claude-sonnet-4` | `anthropic/claude-sonnet-4` | Anthropic |
| `gemini-2.5-pro` | `google/gemini-2.5-pro-preview` | Google |
| `deepseek-r1` | `deepseek/deepseek-r1` | DeepSeek |
| `llama-4-maverick` | `meta-llama/llama-4-maverick` | Meta |
| `qwen-2.5-coder` | `qwen/qwen-2.5-coder-32b-instruct` | Alibaba |

For local or self-hosted models, use `--provider openai` with `--base-url` pointing at any OpenAI-compatible server (vLLM, LM Studio, etc.). Pass the served model id(s) via `--models` — no roster edit required. `OPENAI_API_KEY` is optional for unauthenticated local servers.

#### Prompt Strategies

| Strategy | Description |
|----------|-------------|
| `zero_shot` | Direct prompt with requirements list |
| `few_shot` | 2 working Manim CE examples + target |
| `cot` | Chain-of-thought: 5-step analysis before code |
| `constraint` | Explicit event + coverage + timing constraints |
| `version_aware` | Includes ManimGL→CE incompatibility watchlist |

#### Output Structure

```
results/
├── results_<run_id>.json           # Raw per-trial results
├── logs/
│   ├── run_<run_id>.jsonl          # Structured experiment log
│   └── summary_<run_id>.json       # Aggregated summary
├── generated_code/
│   └── <model>/<strategy>/
│       └── <problem_id>_trial<N>.py  # Generated code files
└── analysis/
    ├── table_model_performance.tex  # LaTeX table for paper
    ├── table_grid_exec.tex          # Model × problem grid
    ├── results_flat.csv             # For plotting
    └── evaluation_report.md         # Markdown summary
```

### Manual Evaluation

For Evaluators:

1. Read **ManiBench_QuickStart.md** (5 min)
2. Pick a problem from **ManiBench_Pilot_Dataset.json** (e.g., MB-005: Determinant)
3. Prompt an LLM using the `full_prompt` field
4. Run the generated code
5. Score using the rubric in **ManiBench_Evaluation_Rubric.md** (10–15 min per trial)

### For LLM Developers

1. Read **ManiBench_Prompt_Engineering_Guide.md** (10 min)
2. Try different prompting strategies on 2–3 problems
3. Identify which strategy yields highest alignment/coverage
4. Iterate and refine

### For Researchers

1. Read **ManiBench_Specification.md** fully (30 min)
2. Review preliminary results (Section 6)
3. Consider experimental variations (e.g., multi-shot prompting, fine-tuning)
4. Contribute additional problems or improved metrics

---

## Key Findings (Preliminary)

From evaluating GPT-4o and Claude 3.5 Sonnet on 12 problems (3 trials each):

**Executability**:
- Simple problems (Level 2): ~100%
- Medium problems (Level 3): ~67%
- Complex problems (Level 4+): ~33%

**Alignment**:
- Simple problems: 0.80–0.90
- Medium problems: 0.60–0.75
- Complex problems: 0.35–0.60

**Common Failure Modes**:
- Missing events (especially temporal updates)
- Wrong event ordering (e.g., loss curve before dot movement)
- Timeout on 3D visualizations (Hairy Ball Theorem)

---

## Extending ManiBench

### Adding Problems (Roadmap to 150–200)

To expand the benchmark:

1. **Identify video sources** from educational channels (3Blue1Brown, Khan Academy, Numberphile)
2. **Extract visual specifications** by carefully watching each video
3. **Write natural language prompts** (target LLMs, not humans)
4. **Annotate required events** with weights and timing constraints
5. **Test with pilot LLMs** (GPT-4o, Claude, open-source)
6. **Refine rubric** based on ambiguities

See **ManiBench_Specification.md** Section 8 for guidance.

### Contributing

If contributing new problems or improvements:
- Follow JSON format in dataset file
- Ensure required events are objective and measurable
- Test prompt with ≥2 LLMs
- Document any new metrics or evaluation challenges
- Open an issue or PR on GitHub

---

## Limitations and Future Work

### Current Limitations
- Manual evaluation of Alignment and Coverage (subjective, time-consuming)
- Limited to Manim CE (not all animation libraries)
- 12 problems may not cover all failure modes
- No user studies validating pedagogical effectiveness

### Future Directions
1. **Automatic Alignment Detection**: Use AST analysis or video frame comparison to score events
2. **Educational Validation**: User studies showing whether animations actually teach concepts
3. **Multi-Library Extension**: Benchmarks for TikZ, Asymptote, Processing, or D3.js
4. **Fine-Tuning Studies**: Can LLMs be fine-tuned on Manim CE code for better performance?
5. **Chain-of-Thought Analysis**: Does reasoning (intermediate thoughts) improve code quality?

---

## Citation

If using ManiBench in academic work:

```bibtex
@article{ManiBench2026,
  title={ManiBench: A Benchmark for Testing Visual-Logic Drift 
         and Syntactic Hallucinations in Manim Code Generation},
  author={Oli, Nabin},
  year={2026},
  institution={Sunway College Kathmandu, Birmingham City University},
  note={HuggingFace: nabin2004/ManiBench}
}
```

---

## License

ManiBench dataset and documentation are provided for research and educational purposes.

---

## Contact

- **Primary Author**: Nabin Oli
- **Affiliation**: Sunway College, Birmingham City University

For questions, suggestions, or contributions, please open an issue.

---

## References

Key works used in ManiBench:

- **Manim**: Grant Sanderson. "Manim: A Python library for creating mathematical animations." https://github.com/3b1b/manim
- **3Blue1Brown Videos**: https://github.com/3b1b/videos

---

## Version History

- **v1.0-pilot** (Feb 2025): Initial release with 12 problems, 4 metrics, evaluation rubric
- **v1.1-pilot** (Feb 2026): Raw code collected for all 12 problems (53K+ lines), reference_code_analysis added with scene inventories, visual techniques, API patterns, and ManimGL→CE version conflict mappings. Schema updated to v2.0. Dataset hosted on HuggingFace.
- **v1.2-pilot** (Feb 2026): Automated evaluation framework added — OpenRouter-based multi-model evaluation pipeline with 4 automated metrics, 5 prompt strategies, structured logging, and paper-ready LaTeX/CSV/Markdown output generation.

---

**Last Updated**: 2026-02-18  
**Schema Version**: 2.0  
**Status**: Pilot dataset complete with full reference code analysis and automated evaluation framework. Ready for paper evaluation.


```Python
uv run python -m evaluation.run --provider openai --base-url https://nabinoli2004--aosqwen-server.us-east.modal.direct/v1 --models aos-qwen2.5-coder-7b-manim
```