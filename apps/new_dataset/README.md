# AOS ManimCE SFT Dataset Preparation & Training

This directory contains the end-to-end pipeline for curating, transforming, validating, and publishing high-quality Supervised Fine-Tuning (SFT) datasets for **Qwen3-8B** and Manim code generation.

The dataset is derived from authentic multi-turn agent execution trajectories in [`nabin2004/AOS-Trajectories`](https://huggingface.co/datasets/nabin2004/AOS-Trajectories), cleaned and converted into pure, standalone **Manim Community Edition (ManimCE)** code with 100% executable syntax.

- **Target Hugging Face Dataset**: [`nabin2004/AOS-Manim-SFT`](https://huggingface.co/datasets/nabin2004/AOS-Manim-SFT)
- **Source Trajectories**: [`nabin2004/AOS-Trajectories`](https://huggingface.co/datasets/nabin2004/AOS-Trajectories)

---

## Key Features

1. **Pure ManimCE Standards**:
   - Strips non-standard runtime dependencies (`VoiceoverScene`, custom speech services).
   - Converts all scenes via Python AST into standard `class <SceneName>(Scene):` with `from manim import *`.
   - Standalone and renderable directly using `manim -ql script.py`.

2. **LaTeX Escape Sequence Repair**:
   - Automatically detects and repairs invalid escape sequences (e.g. `\mathbf`, `\frac`, `\lambda`, `\sum`) in strings by converting them to raw string literals (`r'...'`).
   - Ensures full compatibility with Python 3.12+ with zero `SyntaxWarning` or syntax corruption.

3. **Pedagogical Spatial Reasoning & Planning**:
   - Each assistant response includes a structured visualization and animation plan before the code block.
   - Boosts LLM spatial reasoning, object coordinate planning, and timeline sequencing.

4. **100% AST Syntax Verification**:
   - Every single sample is validated using Python's `ast.parse()` to guarantee 0 syntax errors across 100% of rows.

5. **Qwen Chat Template**:
   - Formatted using standard `messages` schema: `system`, `user`, and `assistant`.

---

## Dataset Structure & Splits

| Split | Sample Count | Format | Description |
|---|---|---|---|
| `train` | **333** | `.jsonl` & `.parquet` | Training split for SFT |
| `validation` | **38** | `.jsonl` & `.parquet` | Evaluation split |
| **Total** | **371** | | 100% unique math/science animation prompts |

### Sample Schema

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are an expert Python programmer specializing in the Manim Community Edition (ManimCE) library. You write clean, executable, and visually appealing mathematical animations. Always plan your spatial layout and animation sequence, then wrap your complete Python code in ```python ... ``` blocks."
    },
    {
      "role": "user",
      "content": "Create a Manim animation that draws a right-angled triangle and labels its sides a, b, and c, then shows the equation a^2 + b^2 = c^2."
    },
    {
      "role": "assistant",
      "content": "Here is the visual and pedagogical plan for the animation:\n1. Define triangle vertices and polygon geometry\n2. Align side labels dynamically relative to edges\n3. Animate equation transformation at the top of the frame\n\n```python\nfrom manim import *\n\nclass PythagoreanTriangle(Scene):\n    def construct(self):\n        ...\n```"
    }
  ]
}
```

---

## Pipeline Scripts

### 1. Prepare Dataset
Fetches trajectories from `nabin2004/AOS-Trajectories`, sanitizes code, executes AST transformations, extracts planning steps, and generates `train.jsonl`, `val.jsonl`, `train.parquet`, and `val.parquet`:

```bash
uv run python prepare_sft_dataset.py
```

### 2. Verify Dataset Quality
Runs automated tests asserting 100% AST syntax correctness, code block regex extraction, and Hugging Face Dataset loading:

```bash
uv run python verify_dataset.py
```

### 3. Upload to Hugging Face
Pushes the dataset splits and metadata card to Hugging Face Hub:

```bash
uv run python upload_to_hf.py --repo-id nabin2004/AOS-Manim-SFT
```

### 4. Finetune Qwen3-8B (QLoRA)
Runs Unsloth-accelerated LoRA training with SFTTrainer:

```bash
uv run python finetune_qwen3.py --dataset-repo nabin2004/AOS-Manim-SFT --epochs 3
```