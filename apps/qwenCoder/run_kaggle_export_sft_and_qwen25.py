#!/usr/bin/env python3
"""One-Click Kaggle Runner for Qwen2.5-Coder-7B GGUF & Qwen3-8B Narrated SFT Merge/GGUF.

Runs in a Kaggle Notebook (GPU or CPU instance, Internet ON):
1. Auto-retrieves HF_TOKEN from Kaggle UserSecretsClient.
2. Clones / builds llama.cpp tools (or downloads precompiled binaries).
3. Executes GGUF conversion & Hub upload for nabin2004/qwen2.5-coder-7b-manim-merged.
4. Executes streaming layer-by-layer merge & GGUF conversion for nabin2004/AOS-qwen3-8b-narrated-adapter.

Usage in Kaggle Cell:
    !git -C /kaggle/working/AOS pull || git clone https://github.com/nabin2004/AOS.git /kaggle/working/AOS
    !python3 /kaggle/working/AOS/apps/qwenCoder/run_kaggle_export_sft_and_qwen25.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

QWEN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = QWEN_ROOT.parent.parent


def get_kaggle_secret(key: str) -> str | None:
    try:
        from kaggle_secrets import UserSecretsClient  # type: ignore

        return UserSecretsClient().get_secret(key)
    except Exception:
        return None


def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"\n$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def ensure_llama_cpp(target_dir: Path) -> Path:
    convert_py = target_dir / "convert_hf_to_gguf.py"
    quant_bin = target_dir / "build" / "bin" / "llama-quantize"

    if convert_py.is_file() and quant_bin.is_file():
        print(f"✔ Using existing llama.cpp in {target_dir}")
        return target_dir

    print(f"⚙ Cloning and building llama.cpp in {target_dir}...")
    if not target_dir.is_dir():
        run_cmd(["git", "clone", "--depth", "1", "https://github.com/ggml-org/llama.cpp", str(target_dir)])

    build_dir = target_dir / "build"
    run_cmd(["cmake", "-S", str(target_dir), "-B", str(build_dir)])
    run_cmd(["cmake", "--build", str(build_dir), "-j"])
    return target_dir


def main() -> int:
    print("=" * 70)
    print("  Kaggle Export Runner: Qwen2.5-Coder-7B GGUF & Qwen3-8B Narrated SFT")
    print("=" * 70)

    # 1. Setup HF_TOKEN
    hf_token = os.environ.get("HF_TOKEN") or get_kaggle_secret("HF_TOKEN")
    if hf_token:
        os.environ["HF_TOKEN"] = hf_token
        print("✔ Authenticated Hugging Face token.")
    else:
        print("Warning: No HF_TOKEN found in environment or Kaggle secrets!")

    # 2. Setup dependencies
    print("\nInstalling runtime requirements...")
    run_cmd([
        sys.executable,
        "-m",
        "pip",
        "install",
        "-q",
        "transformers>=4.48.0",
        "peft>=0.14.0",
        "safetensors>=0.5.0",
        "huggingface-hub>=0.28.0",
        "cmake",
        "gguf>=0.10.0",
    ])

    # 3. Setup llama.cpp
    llama_dir = Path("/kaggle/working/llama.cpp") if Path("/kaggle/working").is_dir() else (QWEN_ROOT / "llama.cpp")
    ensure_llama_cpp(llama_dir)
    os.environ["LLAMA_CPP_DIR"] = str(llama_dir)

    # 4. Run Model 1: Qwen2.5-Coder-7B GGUF
    print("\n" + "=" * 70)
    print("  STAGE 1: Qwen2.5-Coder-7B GGUF Conversion & Push")
    print("=" * 70)
    run_cmd([
        sys.executable,
        str(QWEN_ROOT / "deploy_qwen25_coder_gguf.py"),
    ], cwd=QWEN_ROOT)

    # 5. Run Model 2: Qwen3-8B Narrated SFT Streaming Merge & GGUF
    print("\n" + "=" * 70)
    print("  STAGE 2: Qwen3-8B Narrated SFT Merge & GGUF Push")
    print("=" * 70)
    run_cmd([
        sys.executable,
        str(QWEN_ROOT / "deploy_qwen3_narrated_sft.py"),
    ], cwd=QWEN_ROOT)

    print("\n🎉 All deployments completed successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
