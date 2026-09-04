#!/usr/bin/env python3
"""Push GGUF quantizations and Modelfile to nabin2004/AOS-qwen3-8b-narrated-merged.

This allows users to pull both Safetensors (for transformers/vLLM) and GGUF (for Ollama/llama.cpp)
from the merged repository without encountering:
    "Error: pull model manifest: 400: Repository is not GGUF or is not compatible with llama.cpp"
"""

from __future__ import annotations

import sys
from pathlib import Path
from huggingface_hub import HfApi, get_token

QWEN_ROOT = Path(__file__).resolve().parent
GGUF_DIR = QWEN_ROOT / "qwen3-8b-narrated-gguf"
TARGET_REPO = "nabin2004/AOS-qwen3-8b-narrated-merged"


def main() -> int:
    token = get_token()
    if not token:
        print("ERROR: Hugging Face authentication token not found. Run `huggingface-cli login`.", file=sys.stderr)
        return 1

    api = HfApi(token=token)
    print(f"Target repository: https://huggingface.co/{TARGET_REPO}")

    files_to_upload = [
        "Modelfile",
        "aos-qwen3-8b-narrated-Q4_K_M.gguf",
        "aos-qwen3-8b-narrated-Q8_0.gguf",
    ]

    for fname in files_to_upload:
        fpath = GGUF_DIR / fname
        if not fpath.is_file():
            print(f"Warning: File {fpath} not found, skipping.", file=sys.stderr)
            continue

        size_gb = fpath.stat().st_size / (1024**3)
        print(f"\nUploading {fname} ({size_gb:.2f} GB) to {TARGET_REPO}...")
        try:
            api.upload_file(
                path_or_fileobj=str(fpath),
                path_in_repo=fname,
                repo_id=TARGET_REPO,
                repo_type="model",
                token=token,
            )
            print(f"✔ Successfully uploaded {fname} to {TARGET_REPO}")
        except Exception as e:
            print(f"Failed to upload {fname}: {e}", file=sys.stderr)

    print("\n🎉 GGUF artifacts successfully pushed to merged repository!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
