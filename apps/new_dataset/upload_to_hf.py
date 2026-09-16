#!/usr/bin/env python3
"""Upload the prepared ManimCE SFT Dataset to Hugging Face Hub.

Uploads:
1. train.jsonl & val.jsonl (Standard JSONL chat format)
2. train.parquet & val.parquet (Native Hugging Face Viewer enabled)
3. metadata.json (Dataset metadata)
4. README.md (Comprehensive dataset card with YAML tags and usage examples)

Usage:
    uv run python upload_to_hf.py
    uv run python upload_to_hf.py --repo-id nabin2004/AOS-Manim-SFT
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from huggingface_hub import HfApi, get_token

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = SCRIPT_DIR / "data"
DEFAULT_REPO_ID = "nabin2004/AOS-Manim-SFT"


def generate_dataset_card(repo_id: str, num_train: int, num_val: int) -> str:
    return f"""---
license: mit
task_categories:
- text-generation
language:
- en
- code
tags:
- manim
- manimce
- mathematical-animation
- qwen
- qwen3
- code-generation
- sft
- educational
size_categories:
- n<1k
configs:
- config_name: default
  data_files:
  - split: train
    path: train.parquet
  - split: validation
    path: val.parquet
---

# {repo_id.split('/')[-1]} (AOS ManimCE SFT Dataset)

Curated, high-quality Supervised Fine-Tuning (SFT) dataset for training **Qwen3-8B** and frontier code models to generate executable, visually appealing mathematical animations using **Manim Community Edition (ManimCE)**.

Derived and refined from authentic multi-turn code agent execution trajectories in [`nabin2004/AOS-Trajectories`](https://huggingface.co/datasets/nabin2004/AOS-Trajectories).

---

## Key Characteristics

- **100% AST Syntax Verified**: Every single code snippet passes Python `ast.parse()` with zero syntax errors.
- **Pure Standard ManimCE**: All scenes inherit from `Scene` and use community-standard ManimCE imports (`from manim import *`). Standalone and executable via `manim -ql scene.py`.
- **LaTeX Escape Sequence Clean**: All mathematical expressions (`\\mathbf`, `\\frac`, `\\lambda`, `\\sum`) are properly formatted as raw string literals to prevent escape sequence warnings.
- **Pedagogical Spatial Reasoning**: Assistant responses feature a visual and pedagogical planning outline prior to the code fence, boosting model spatial reasoning and visual accuracy.
- **Qwen Chat Template**: Formatted cleanly with `system`, `user`, and `assistant` message objects.

---

## Dataset Splits

| Split | Rows | Format | Description |
|---|---|---|---|
| `train` | **{num_train}** | JSONL & Parquet | Training split for SFT |
| `validation` | **{num_val}** | JSONL & Parquet | Evaluation split for validation loss & generation |
| **Total** | **{num_train + num_val}** | | Curated, unique educational trajectories |

---

## Sample Format

```json
{{
  "messages": [
    {{
      "role": "system",
      "content": "You are an expert Python programmer specializing in the Manim Community Edition (ManimCE) library. You write clean, executable, and visually appealing mathematical animations. Always plan your spatial layout and animation sequence, then wrap your complete Python code in ```python ... ``` blocks."
    }},
    {{
      "role": "user",
      "content": "Create a Manim animation explaining eigenvectors and eigenvalues with 2D transformations and dynamic coordinate labels."
    }},
    {{
      "role": "assistant",
      "content": "Here is the visual and pedagogical plan for the animation:\\n1. Introduction - Opening title\\n2. The Defining Equation - Shows A v = lambda v\\n...\\n\\n```python\\nfrom manim import *\\n\\nclass EigenvalueScene(Scene):\\n    def construct(self):\\n        ...\\n```"
    }}
  ]
}}
```

---

## Quickstart & Training

### 1. Load with Hugging Face Datasets

```python
from datasets import load_dataset

dataset = load_dataset("{repo_id}")
print(dataset)
# DatasetDict({{
#     train: Dataset({{ features: ['messages'], num_rows: {num_train} }}),
#     validation: Dataset({{ features: ['messages'], num_rows: {num_val} }})
# }})
```

### 2. Finetune Qwen3-8B with Unsloth / SFTTrainer

```python
from datasets import load_dataset
from trl import SFTTrainer
from unsloth import FastLanguageModel

# Load Qwen3-8B
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen3-8B",
    max_seq_length=2048,
    load_in_4bit=True,
)

# Apply LoRA
model = FastLanguageModel.get_peft_model(
    model,
    r=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none",
)

# Format with Qwen chat template
def formatting_prompts_func(examples):
    texts = tokenizer.apply_chat_template(
        examples["messages"],
        tokenize=False,
        add_generation_prompt=False,
    )
    return {{"text": texts}}

dataset = load_dataset("{repo_id}", split="train")
dataset = dataset.map(formatting_prompts_func, batched=True)
```

---

## Curation Pipeline

Engineered in `apps/new_dataset` of the [AOS (Agentic Orchestration System)](https://github.com/nabin2004/AOS) repository.
"""


def upload_dataset(repo_id: str, data_dir: Path) -> None:
    token = os.environ.get("HF_TOKEN") or get_token()
    if not token:
        print("ERROR: HF_TOKEN not found. Run `huggingface-cli login` or export HF_TOKEN.", file=sys.stderr)
        sys.exit(1)

    api = HfApi(token=token)
    user = api.whoami(token=token)
    print(f"Authenticated as: {user.get('name')}")

    print(f"Creating / verifying Hub dataset repo: {repo_id}...")
    api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, token=token)

    # Count rows
    train_file = data_dir / "train.jsonl"
    val_file = data_dir / "val.jsonl"

    num_train = sum(1 for line in open(train_file, "r", encoding="utf-8") if line.strip())
    num_val = sum(1 for line in open(val_file, "r", encoding="utf-8") if line.strip())

    # Generate and write dataset card
    dataset_card_content = generate_dataset_card(repo_id, num_train, num_val)
    card_path = data_dir / "README.md"
    with open(card_path, "w", encoding="utf-8") as f:
        f.write(dataset_card_content)

    files_to_upload = [
        (train_file, "train.jsonl"),
        (val_file, "val.jsonl"),
        (data_dir / "train.parquet", "train.parquet"),
        (data_dir / "val.parquet", "val.parquet"),
        (data_dir / "metadata.json", "metadata.json"),
        (card_path, "README.md"),
    ]

    for local_path, hub_name in files_to_upload:
        if not local_path.is_file():
            print(f"Skipping missing file: {local_path}")
            continue
        print(f"Uploading {local_path.name} -> {repo_id}/{hub_name}...")
        api.upload_file(
            path_or_fileobj=str(local_path),
            path_in_repo=hub_name,
            repo_id=repo_id,
            repo_type="dataset",
            token=token,
        )

    print("\n" + "=" * 60)
    print(f"🚀 SUCCESS: Uploaded dataset to https://huggingface.co/datasets/{repo_id}")
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload ManimCE SFT Dataset to Hugging Face")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID, help=f"Hugging Face dataset repository (default: {DEFAULT_REPO_ID})")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Data directory with jsonl and parquet files")
    args = parser.parse_args()

    upload_dataset(repo_id=args.repo_id, data_dir=args.data_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
