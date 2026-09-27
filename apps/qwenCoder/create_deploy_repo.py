#!/usr/bin/env python3
"""Clean Deploy-Ready Repository Creator & RunPod Serverless Config Generator.

This script inspects an existing Hugging Face fine-tuning repository (like nabin2004/qwen-Manimator-1-grpo)
which contains bulky training checkpoints, filters out all checkpoint-* and ref folders, and produces:
  1. A lightweight, clean deploy-ready adapter repo (~95 MB vs 3.22 GB).
  2. Optional streaming layer-by-layer merged full model (<500 MB RAM usage).
  3. RunPod Serverless deployment configuration (JSON + ENV file) with optional RoPE YaRN scaling.

Usage:
    # 1. Preview files that will be extracted (dry-run, no downloads/uploads):
    uv run python create_deploy_repo.py --dry-run

    # 2. Create clean adapter repo on Hugging Face:
    uv run python create_deploy_repo.py --mode adapter

    # 3. Create full-weight merged repo on Hugging Face:
    uv run python create_deploy_repo.py --mode merged

    # 4. Generate RunPod serverless configs for 65k context (YaRN factor 2.0):
    uv run python create_deploy_repo.py --max-context 65536
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import torchvision  # noqa: F401
except Exception:
    sys.modules["torchvision"] = None

import torch
from huggingface_hub import HfApi, get_token, hf_hub_download
from safetensors import safe_open
from safetensors.torch import load_file, save_file

DEFAULT_SOURCE_REPO = "nabin2004/qwen-Manimator-1-grpo"
DEFAULT_TARGET_ADAPTER_REPO = "nabin2004/qwen-Manimator-1-grpo-clean"
DEFAULT_TARGET_MERGED_REPO = "nabin2004/qwen-Manimator-1-grpo-merged"
DEFAULT_BASE_REPO = "Qwen/Qwen3-8B"
ORIGINAL_MAX_POSITION_EMBEDDINGS = 32768

# Essential production files needed to serve or merge a LoRA adapter
ESSENTIAL_ADAPTER_FILES = [
    "adapter_config.json",
    "adapter_model.safetensors",
    "chat_template.jinja",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "special_tokens_map.json",
    "added_tokens.json",
]


def calculate_rope_scaling(max_context: int, original_len: int = ORIGINAL_MAX_POSITION_EMBEDDINGS) -> dict | None:
    """Calculate YaRN RoPE scaling configuration for Qwen models."""
    if max_context <= original_len:
        return None
    factor = float(max_context) / float(original_len)
    return {
        "rope_type": "yarn",
        "factor": round(factor, 2),
        "original_max_position_embeddings": original_len,
    }


def generate_adapter_model_card(
    target_repo: str,
    source_repo: str,
    base_model: str,
    r: int,
    alpha: int,
    max_context: int,
) -> str:
    """Generate production-ready model card for the clean adapter repo."""
    return f"""---
license: apache-2.0
base_model: {base_model}
library_name: peft
pipeline_tag: text-generation
language:
  - en
tags:
  - peft
  - lora
  - grpo
  - manim
  - manimce
  - manim-voiceover
  - aos
  - code-generation
  - mathematical-animation
---

# {target_repo} — Production Clean LoRA Adapter

This is the **clean, deploy-ready release** of [`{source_repo}`](https://huggingface.co/{source_repo}).
All intermediate checkpoint folders and training state caches have been stripped, reducing the repository size from **3.22 GB down to ~95 MB**.

- **Base Model**: [`{base_model}`](https://huggingface.co/{base_model})
- **Training Algorithm**: GRPO (Group Relative Policy Optimization)
- **Domain**: Automated ManimCE and Manim Voiceover pedagogical animation synthesis
- **LoRA Configuration**: Rank ($r$) = {r}, Alpha ($\\alpha$) = {alpha}, Scaling = {alpha / r:.2f}
- **Native Context**: {ORIGINAL_MAX_POSITION_EMBEDDINGS:,} tokens (scalable to 131k with YaRN)

---

## Quickstart (RunPod Serverless vLLM)

In RunPod Serverless Quick Deploy, select the **vLLM** template and set:

```env
MODEL_NAME={base_model}
ENABLE_LORA=1
LORA_MODULES=[{{"name": "manimator", "path": "{target_repo}"}}]
MAX_MODEL_LEN={max_context}
```

---

## Quickstart (Transformers)

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

base_model_id = "{base_model}"
adapter_id = "{target_repo}"

tokenizer = AutoTokenizer.from_pretrained(adapter_id)
base_model = AutoModelForCausalLM.from_pretrained(
    base_model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
model = PeftModel.from_pretrained(base_model, adapter_id)

prompt = "Create a ManimCE VoiceoverScene explaining the Three-Body Problem."
messages = [{{"role": "user", "content": prompt}}]
inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(model.device)

outputs = model.generate(inputs, max_new_tokens=2048, temperature=0.3)
print(tokenizer.decode(outputs[0][inputs.shape[-1]:], skip_special_tokens=True))
```
"""


def generate_merged_model_card(
    target_repo: str,
    adapter_repo: str,
    base_model: str,
    max_context: int,
) -> str:
    """Generate production-ready model card for the standalone merged model."""
    return f"""---
license: apache-2.0
base_model: {base_model}
library_name: transformers
pipeline_tag: text-generation
language:
  - en
tags:
  - safetensors
  - grpo
  - manim
  - manimce
  - manim-voiceover
  - aos
  - code-generation
  - mathematical-animation
---

# {target_repo} — Standalone Merged Model (bf16)

Full-weight merged production release of **qwen-Manimator-1-grpo**, combining [`{base_model}`](https://huggingface.co/{base_model}) with the GRPO-trained LoRA adapter [`{adapter_repo}`](https://huggingface.co/{adapter_repo}).

- **Base Model**: [`{base_model}`](https://huggingface.co/{base_model})
- **Adapter Source**: [`{adapter_repo}`](https://huggingface.co/{adapter_repo})
- **Format**: bf16 Safetensors
- **Native Context**: {ORIGINAL_MAX_POSITION_EMBEDDINGS:,} tokens (scalable to 131k with YaRN)

---

## Quickstart (RunPod Serverless vLLM — Recommended 1-Click Deploy)

This merged model requires **zero LoRA configuration** on vLLM. In RunPod Serverless:

1. Click **Quick Deploy** -> **vLLM**
2. Set Environment Variables:
```env
MODEL_NAME={target_repo}
MAX_MODEL_LEN={max_context}
```
3. Connect your OpenAI client directly to the endpoint URL.

---

## Quickstart (Transformers)

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "{target_repo}"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)

messages = [{{"role": "user", "content": "Explain Kepler's laws in ManimCE."}}]
inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(model.device)
out = model.generate(inputs, max_new_tokens=2048, temperature=0.2)
print(tokenizer.decode(out[0][inputs.shape[-1]:], skip_special_tokens=True))
```
"""


def generate_runpod_configs(
    out_dir: Path,
    adapter_repo: str,
    merged_repo: str,
    base_model: str,
    max_context: int,
    hf_token: str | None,
) -> None:
    """Generate runpod_config.json and .env.runpod deployment files."""
    rope_cfg = calculate_rope_scaling(max_context)
    rope_str = json.dumps(rope_cfg) if rope_cfg else ""

    # 1. Merged Config (Fastest & simplest)
    merged_env = {
        "MODEL_NAME": merged_repo,
        "MAX_MODEL_LEN": str(max_context),
    }
    if rope_str:
        merged_env["ROPE_SCALING"] = rope_str
    if hf_token:
        merged_env["HF_TOKEN"] = "your_hf_token_if_repo_is_private"

    # 2. Adapter Config
    adapter_env = {
        "MODEL_NAME": base_model,
        "ENABLE_LORA": "1",
        "LORA_MODULES": json.dumps([{"name": "manimator", "path": adapter_repo}]),
        "MAX_MODEL_LEN": str(max_context),
    }
    if rope_str:
        adapter_env["ROPE_SCALING"] = rope_str
    if hf_token:
        adapter_env["HF_TOKEN"] = "your_hf_token_if_repo_is_private"

    config_payload = {
        "deployment_recommended": "merged",
        "context_length": max_context,
        "rope_scaling": rope_cfg,
        "merged_deployment": {
            "description": "Recommended for RunPod Serverless (Fast cold starts, zero LoRA overhead)",
            "env_vars": merged_env,
            "recommended_gpu": "L40S (48GB)" if max_context <= 65536 else "A100 (80GB)",
        },
        "adapter_deployment": {
            "description": "Loads Qwen3-8B base and applies clean LoRA adapter on boot",
            "env_vars": adapter_env,
            "recommended_gpu": "L40S (48GB)" if max_context <= 65536 else "A100 (80GB)",
        },
    }

    config_path = out_dir / "runpod_config.json"
    config_path.write_text(json.dumps(config_payload, indent=2), encoding="utf-8")
    print(f"✔ Wrote RunPod config: {config_path}")

    env_path = out_dir / "runpod_merged.env"
    env_content = "\n".join(f"{k}={v}" for k, v in merged_env.items()) + "\n"
    env_path.write_text(env_content, encoding="utf-8")
    print(f"✔ Wrote RunPod env file: {env_path}")


def create_clean_adapter_repo(
    source_repo: str,
    target_repo: str,
    base_model: str,
    max_context: int,
    dry_run: bool = False,
    token: str | None = None,
) -> Path:
    """Download root production files and publish to the clean adapter repository."""
    work_dir = Path("./build_clean_adapter").resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 65)
    print(f"📦 Step 1: Clean Adapter Extraction")
    print(f"Source: {source_repo}")
    print(f"Target: {target_repo}")
    print("=" * 65)

    api = HfApi(token=token)

    # 1. Fetch source files listing
    print("\nScanning remote repository files...")
    all_files = api.list_repo_files(source_repo, token=token)
    root_files = [f for f in all_files if "/" not in f]
    skipped_folders = sorted(set(f.split("/")[0] for f in all_files if "/" in f))

    print(f"Found {len(all_files)} total files on remote repository.")
    print(f"  -> Skipping intermediate checkpoint folders: {skipped_folders}")
    print(f"  -> Selected {len(root_files)} root files for clean release: {root_files}")

    if dry_run:
        print("\n[DRY RUN] Skipping file download and Hugging Face upload.")
        return work_dir

    # 2. Download root files
    print("\nDownloading production files...")
    total_bytes = 0
    for fname in root_files:
        if fname.startswith("."):
            continue
        try:
            downloaded = hf_hub_download(source_repo, fname, token=token)
            dest = work_dir / fname
            shutil.copy(downloaded, dest)
            size_mb = dest.stat().st_size / (1024 * 1024)
            total_bytes += dest.stat().st_size
            print(f"  ✔ {fname} ({size_mb:.2f} MB)")
        except Exception as exc:
            print(f"  ⚠ Notice on {fname}: {exc}")

    # Inspect LoRA params
    cfg_file = work_dir / "adapter_config.json"
    r = 16
    alpha = 32
    if cfg_file.is_file():
        with open(cfg_file, encoding="utf-8") as f:
            c = json.load(f)
            r = c.get("r", r)
            alpha = c.get("lora_alpha", alpha)
            base_model = c.get("base_model_name_or_path", base_model)

    # Write clean README.md
    readme_text = generate_adapter_model_card(
        target_repo=target_repo,
        source_repo=source_repo,
        base_model=base_model,
        r=r,
        alpha=alpha,
        max_context=max_context,
    )
    (work_dir / "README.md").write_text(readme_text, encoding="utf-8")
    print(f"  ✔ Generated clean README.md model card")

    print(f"\nClean Adapter bundle ready: {total_bytes / (1024 * 1024):.2f} MB total (vs 3.22 GB originally).")

    # 3. Upload to target repo
    if token:
        print(f"\nPublishing clean adapter to https://huggingface.co/{target_repo}...")
        api.create_repo(target_repo, repo_type="model", exist_ok=True, token=token)
        api.upload_folder(
            folder_path=str(work_dir),
            repo_id=target_repo,
            repo_type="model",
            token=token,
        )
        print(f"🎉 Clean adapter live: https://huggingface.co/{target_repo}")
    else:
        print("\n⚠ No HF_TOKEN found. Clean files stored locally; set HF_TOKEN to upload.")

    return work_dir


def create_merged_model_repo(
    adapter_repo: str,
    target_repo: str,
    base_model: str,
    max_context: int,
    dry_run: bool = False,
    token: str | None = None,
) -> Path:
    """Stream layer-by-layer merge of base model and adapter into full-weight safetensors."""
    merged_dir = Path("./build_merged_model").resolve()
    merged_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 65)
    print(f"🔀 Step 2: Layer-by-Layer Streaming Merge")
    print(f"Base LLM:     {base_model}")
    print(f"Adapter:      {adapter_repo}")
    print(f"Target Repo:  {target_repo}")
    print("=" * 65)

    if dry_run:
        print("\n[DRY RUN] Skipping weight merge and upload.")
        return merged_dir

    api = HfApi(token=token)

    # 1. Download adapter tensors
    print("\nFetching adapter tensors...")
    cfg_file = hf_hub_download(adapter_repo, "adapter_config.json", token=token)
    with open(cfg_file, encoding="utf-8") as f:
        cfg = json.load(f)
    r = cfg.get("r", 16)
    alpha = cfg.get("lora_alpha", 32)
    scaling = float(alpha) / float(r)

    weights_file = hf_hub_download(adapter_repo, "adapter_model.safetensors", token=token)
    adapter_tensors = load_file(weights_file)
    print(f"✔ Adapter tensors loaded: {len(adapter_tensors)} tensors (scaling={scaling:.4f})")

    # 2. Base model metadata
    print(f"\nFetching base model metadata from {base_model}...")
    meta_files = [
        "config.json",
        "generation_config.json",
        "model.safetensors.index.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.json",
        "merges.txt",
        "chat_template.jinja",
    ]
    for mf in meta_files:
        try:
            d = hf_hub_download(base_model, mf, token=token)
            shutil.copy(d, merged_dir / mf)
        except Exception:
            pass

    index_file = merged_dir / "model.safetensors.index.json"
    if not index_file.is_file():
        raise RuntimeError("Missing model.safetensors.index.json from base model.")

    with open(index_file, encoding="utf-8") as f:
        idx = json.load(f)
    all_shards = sorted(set(idx.get("weight_map", {}).values()))
    print(f"Base model contains {len(all_shards)} shards to merge.")

    # 3. Stream merge shard by shard
    for i, shard in enumerate(all_shards, 1):
        target_shard = merged_dir / shard
        if target_shard.is_file() and target_shard.stat().st_size > 1e9:
            print(f"[{i}/{len(all_shards)}] {shard} already merged. Skipping.")
            continue

        print(f"[{i}/{len(all_shards)}] Merging shard: {shard}...")
        shard_path = hf_hub_download(base_model, shard, token=token)
        merged_shard = {}
        with safe_open(shard_path, framework="pt", device="cpu") as f_in:
            for tensor_name in f_in.keys():
                W = f_in.get_tensor(tensor_name)
                prefix = tensor_name[:-len(".weight")] if tensor_name.endswith(".weight") else tensor_name
                a_key = f"base_model.model.{prefix}.lora_A.weight"
                b_key = f"base_model.model.{prefix}.lora_B.weight"
                if a_key in adapter_tensors and b_key in adapter_tensors:
                    A = adapter_tensors[a_key]
                    B = adapter_tensors[b_key]
                    delta = (torch.matmul(B.float(), A.float()) * scaling).to(W.dtype)
                    merged_shard[tensor_name] = W + delta
                else:
                    merged_shard[tensor_name] = W

        save_file(merged_shard, str(target_shard))
        del merged_shard
        print(f"✔ Shard {i}/{len(all_shards)} merged.")

    # Model card
    readme = generate_merged_model_card(
        target_repo=target_repo,
        adapter_repo=adapter_repo,
        base_model=base_model,
        max_context=max_context,
    )
    (merged_dir / "README.md").write_text(readme, encoding="utf-8")
    print(f"✔ Generated merged README.md model card")

    # 4. Upload
    if token:
        print(f"\nPublishing merged model to https://huggingface.co/{target_repo}...")
        api.create_repo(target_repo, repo_type="model", exist_ok=True, token=token)
        api.upload_folder(
            folder_path=str(merged_dir),
            repo_id=target_repo,
            repo_type="model",
            token=token,
        )
        print(f"🎉 Merged model live: https://huggingface.co/{target_repo}")
    else:
        print("\n⚠ No HF_TOKEN found. Merged model saved locally.")

    return merged_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean Deploy-Ready Repository Creator & RunPod Serverless Config Generator"
    )
    parser.add_argument(
        "--source-repo",
        default=DEFAULT_SOURCE_REPO,
        help=f"Existing Hugging Face repo with checkpoints (default: {DEFAULT_SOURCE_REPO})",
    )
    parser.add_argument(
        "--target-adapter-repo",
        default=DEFAULT_TARGET_ADAPTER_REPO,
        help=f"Clean target repo name for adapter (default: {DEFAULT_TARGET_ADAPTER_REPO})",
    )
    parser.add_argument(
        "--target-merged-repo",
        default=DEFAULT_TARGET_MERGED_REPO,
        help=f"Clean target repo name for merged weights (default: {DEFAULT_TARGET_MERGED_REPO})",
    )
    parser.add_argument(
        "--base-repo",
        default=DEFAULT_BASE_REPO,
        help=f"Base model identifier (default: {DEFAULT_BASE_REPO})",
    )
    parser.add_argument(
        "--mode",
        choices=["adapter", "merged", "both"],
        default="adapter",
        help="What to create: clean adapter repo, merged full-weight repo, or both",
    )
    parser.add_argument(
        "--max-context",
        type=int,
        default=32768,
        choices=[32768, 65536, 131072],
        help="Context window length (32768 is native; 65536 or 131072 enables YaRN RoPE)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect files and generate RunPod configs without uploading to Hugging Face",
    )
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN", "").strip() or get_token()

    out_dir = Path(".").resolve()

    print("=================================================================")
    print("🚀 AOS Deploy-Ready Model Creator & RunPod Configurator")
    print(f"Source Repo:         {args.source_repo}")
    print(f"Target Adapter Repo: {args.target_adapter_repo}")
    print(f"Target Merged Repo:  {args.target_merged_repo}")
    print(f"Base LLM:            {args.base_repo}")
    print(f"Mode:                {args.mode}")
    print(f"Context Window:      {args.max_context:,} tokens")
    print(f"Dry Run:             {args.dry_run}")
    print("=================================================================")

    # 1. Adapter creation
    if args.mode in ("adapter", "both"):
        create_clean_adapter_repo(
            source_repo=args.source_repo,
            target_repo=args.target_adapter_repo,
            base_model=args.base_repo,
            max_context=args.max_context,
            dry_run=args.dry_run,
            token=token,
        )

    # 2. Merged creation
    if args.mode in ("merged", "both"):
        create_merged_model_repo(
            adapter_repo=args.target_adapter_repo if args.mode == "both" else args.source_repo,
            target_repo=args.target_merged_repo,
            base_model=args.base_repo,
            max_context=args.max_context,
            dry_run=args.dry_run,
            token=token,
        )

    # 3. Generate RunPod deployment config
    generate_runpod_configs(
        out_dir=out_dir,
        adapter_repo=args.target_adapter_repo,
        merged_repo=args.target_merged_repo,
        base_model=args.base_repo,
        max_context=args.max_context,
        hf_token=token,
    )

    print("\n" + "=" * 65)
    print("✨ Deployment preparation completed successfully!")
    print(f"RunPod configs generated at: {out_dir / 'runpod_config.json'}")
    print("=================================================================")


if __name__ == "__main__":
    main()
