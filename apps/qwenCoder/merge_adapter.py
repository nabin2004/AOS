#!/usr/bin/env python3
"""Merge a Qwen LoRA adapter into bf16 base weights.

Supports both local adapter directories and remote Hugging Face Hub adapter IDs.

Usage (from apps/qwenCoder):

    uv run python merge_adapter.py \
      --adapter-dir nabin2004/AOS-qwen3-8b-narrated-dpo \
      --model-id Qwen/Qwen3-8B \
      --output-dir ./qwen3-8b-narrated-merged \
      --push-to-hub \
      --hub-repo-id nabin2004/AOS-qwen3-8b-narrated-merged
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Guard against broken/incompatible local torchvision binary installations
try:
    import torchvision  # noqa: F401
except Exception:
    sys.modules["torchvision"] = None

import torch
from huggingface_hub import snapshot_download
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from hub_upload import push_model_folder, require_token
from identity import BASE_MODEL_ID, HUB_MERGED_REPO


def _hub_token() -> str | None:
    return os.environ.get("HF_TOKEN", "").strip() or None


def resolve_adapter_path(adapter_input: str, token: str | None) -> str:
    """Resolve an adapter input string to a local directory or download it from HF Hub."""
    local_path = Path(adapter_input).expanduser()
    if local_path.is_dir() and (local_path / "adapter_config.json").is_file():
        return str(local_path.resolve())

    # If it's a directory without adapter_config, or not a directory, try HF Hub download
    print(f"Resolving adapter from Hugging Face Hub: {adapter_input}...")
    try:
        downloaded = snapshot_download(
            repo_id=adapter_input,
            repo_type="model",
            token=token,
        )
        print(f"✔ Downloaded adapter snapshot to {downloaded}")
        return downloaded
    except Exception as exc:
        if local_path.is_dir():
            print(f"Warning: Hub download failed ({exc}), using local dir {local_path}")
            return str(local_path.resolve())
        raise FileNotFoundError(
            f"Could not resolve adapter '{adapter_input}' as a local path or Hugging Face repository: {exc}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--adapter-dir",
        "--adapter-id",
        dest="adapter_id",
        required=True,
        help="Local directory or Hugging Face repo ID of the LoRA adapter",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to save merged bf16 weights and tokenizer",
    )
    parser.add_argument(
        "--model-id",
        default=BASE_MODEL_ID,
        help=f"Base model ID (default: {BASE_MODEL_ID})",
    )
    parser.add_argument(
        "--device",
        default="auto" if torch.cuda.is_available() else "cpu",
        choices=["auto", "cpu", "cuda"],
        help="Device to perform the merge on ('auto', 'cuda', 'cpu')",
    )
    parser.add_argument(
        "--readme-path",
        type=Path,
        default=None,
        help="Optional path to custom README.md model card to include in output",
    )
    parser.add_argument(
        "--push-to-hub",
        action="store_true",
        help="Upload merged model to Hugging Face Hub",
    )
    parser.add_argument(
        "--hub-repo-id",
        default=HUB_MERGED_REPO,
        help=f"Target HF repo ID for merged weights (default: {HUB_MERGED_REPO})",
    )
    parser.add_argument(
        "--hub-private",
        action="store_true",
        help="Upload as a private repository",
    )
    args = parser.parse_args()

    token = _hub_token()
    resolved_adapter = resolve_adapter_path(args.adapter_id, token)
    output_dir = args.output_dir.expanduser().resolve()

    print(f"Loading base {args.model_id} (dtype=bf16, device={args.device})...")
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_id, trust_remote_code=True, token=token
    )

    device_map = args.device if args.device != "cuda" else {"": "cuda:0"}
    base = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        torch_dtype=torch.bfloat16,
        device_map=device_map,
        trust_remote_code=True,
        token=token,
    )

    print(f"Loading adapter from {resolved_adapter}...")
    model = PeftModel.from_pretrained(base, resolved_adapter, token=token)

    print("Merging LoRA weights into base model...")
    model = model.merge_and_unload()

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Saving merged safetensors to {output_dir}...")
    model.save_pretrained(str(output_dir), safe_serialization=True)
    tokenizer.save_pretrained(str(output_dir))

    if args.readme_path and args.readme_path.is_file():
        readme_dest = output_dir / "README.md"
        readme_dest.write_text(args.readme_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Wrote model card to {readme_dest}")

    print(f"✔ Merged model successfully saved to {output_dir}")

    if args.push_to_hub:
        hub_token = require_token()
        push_model_folder(
            output_dir,
            args.hub_repo_id,
            hub_token,
            private=args.hub_private,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
