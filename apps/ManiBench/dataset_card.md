---
license: mit
task_categories:
  - text-generation
language:
  - en
tags:
  - manim
  - code-generation
  - math-visualization
  - benchmark
  - evaluation
  - visual-logic-drift
  - syntactic-hallucination
  - animation
pretty_name: ManiBench
size_categories:
  - n<1K
---

# ManiBench: A Benchmark for Testing Visual-Logic Drift and Syntactic Hallucinations in Manim Code Generation

## Overview

**ManiBench** is a specialized benchmark dataset for evaluating Large Language Model (LLM) performance in generating [Manim CE](https://www.manim.community/) (Community Edition) code — mathematical animations used for educational content creation.

This benchmark addresses two critical failure modes in LLM-generated code:

1. **Syntactic Hallucinations**: Code that appears valid in Python but references non-existent Manim functions, uses deprecated APIs, or breaks under specific library versions.
2. **Visual-Logic Drift**: Code that executes without errors but produces incorrect, incomplete, or misaligned animations that fail to communicate the intended mathematical concept.

## Dataset Structure

### Pilot Dataset (`ManiBench_Pilot_Dataset.json`)

12 problems spanning multiple mathematical domains:

| ID | Title | Difficulty | Domain |
|----|-------|-----------|--------|
| MB-001 | Colliding Blocks Compute π | 4 | Physics, Numerics |
| MB-002 | Gradient Descent, How Neural Networks Learn | 3 | ML, Calculus |
| MB-003 | But What Is a Convolution? | 3 | Signal Processing, Linear Algebra |
| MB-004 | Eigenvectors & Eigenvalues | 4 | Linear Algebra |
| MB-005 | The Determinant | 2 | Linear Algebra |
| MB-006 | Central Limit Theorem | 3 | Probability, Statistics |
| MB-007 | The Medical Test Paradox | 2 | Probability, Bayes |
| MB-008 | Visualizing the Chain Rule | 3 | Calculus |
| MB-009 | Fundamental Theorem of Calculus | 3 | Calculus, Integration |
| MB-010 | Taylor Series | 4 | Calculus, Series |
| MB-011 | The Hairy Ball Theorem | 5 | Topology, Vector Fields |
| MB-012 | The Windmill Problem | 4 | Geometry, Combinatorics |

### Each problem includes:
- **Prompt**: Full natural-language specification for code generation
- **Required Visual Events**: Weighted, timestamped events the animation must contain
- **Coverage Requirements**: Pedagogical elements that must be present
- **Success Criteria**: Minimum scores for executability, alignment, coverage, and version-conflict error rate
- **Common Failure Modes**: Known ways LLMs fail on each problem (with severity tags)
- **Version Conflict Notes**: CE vs GL API incompatibilities

### Reference Code (`raw_code/`)
- MB-001 includes 3Blue1Brown's original Manim GL source code (2193+ lines) for cross-reference

## Evaluation Metrics

| Metric | Description |
|--------|-------------|
| **Executability** | Binary: does the generated code run without errors? |
| **Version-Conflict Error Rate** | % of errors from API version mismatches |
| **Alignment Score** | Weighted match of required visual events (0–1) |
| **Coverage Score** | Pedagogical content density (0–1) |

## Usage

```python
import json

with open("ManiBench_Pilot_Dataset.json") as f:
    data = json.load(f)

for problem in data["problems"]:
    print(f"{problem['id']}: {problem['title']} (Level {problem['difficulty_level']})")
    print(f"  Events: {len(problem['required_visual_events'])}")
    print(f"  Prompt: {problem['full_prompt'][:100]}...")
```

## Supporting Documents

| File | Description |
|------|-------------|
| `ManiBench_Specification.md` | Full research paper |
| `ManiBench_Evaluation_Rubric.md` | Detailed scoring methodology |
| `ManiBench_Prompt_Engineering_Guide.md` | Guide for prompt construction |
| `ManiBench_QuickStart.md` | Quick start guide |

## Citation

If you use ManiBench in your research, please cite:

```bibtex
@dataset{manibench2026,
  title={ManiBench: A Benchmark for Testing Visual-Logic Drift and Syntactic Hallucinations in Manim Code Generation},
  author={nabin2004},
  year={2026},
  url={https://huggingface.co/datasets/nabin2004/ManiBench}
}
```

## License

MIT
