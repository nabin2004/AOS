#!/usr/bin/env python3
"""One-Click Kaggle Runner for AOS Qwen3-8B Narrated Merging, GGUF Multi-Quant & Hub Deploy.

Runs in a Kaggle Notebook (GPU or CPU instance, Internet ON):
1. Retrieves HF_TOKEN automatically from Kaggle UserSecretsClient.
2. Clones and compiles llama.cpp with parallel cmake in /kaggle/working/llama.cpp (~45 seconds).
3. Merges LoRA adapter (nabin2004/AOS-qwen3-8b-narrated-dpo) with Qwen/Qwen3-8B in bf16.
4. Generates model cards and pushes merged Safetensors repo: nabin2004/AOS-qwen3-8b-narrated-merged.
5. Converts to GGUF and quantizes into Q4_K_M (~5.0 GB) and Q8_0 (~8.5 GB).
6. Generates Ollama Modelfile and pushes GGUF repo: nabin2004/AOS-qwen3-8b-narrated-gguf.

Usage in Kaggle Notebook code cell:
    !python3 apps/qwenCoder/run_kaggle_narrated_deploy.py
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

QWEN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = QWEN_ROOT.parent.parent


def setup_kaggle_secrets() -> None:
    """Retrieve HF_TOKEN from Kaggle UserSecrets if present."""
    if "HF_TOKEN" not in os.environ:
        try:
            from kaggle_secrets import UserSecretsClient  # type: ignore

            secrets = UserSecretsClient()
            token = secrets.get_secret("HF_TOKEN")
            if token:
                os.environ["HF_TOKEN"] = token
                print("✔ Successfully loaded HF_TOKEN from Kaggle UserSecrets.")
        except Exception as exc:
            print(f"Notice: Could not load HF_TOKEN from Kaggle secrets: {exc}")


def install_deployment_dependencies() -> None:
    """Ensure transformers, peft, accelerate, and huggingface_hub are installed."""
    print("\n==> Ensuring deployment dependencies are installed...")
    python_exe = sys.executable
    subprocess.run(
        [
            python_exe,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "transformers>=4.51.0",
            "peft>=0.19.1",
            "accelerate>=1.0.0",
            "huggingface-hub>=0.27.0",
        ],
        check=True,
    )


def build_llama_cpp(target_dir: Path) -> Path:
    """Clone and compile llama.cpp if not already present."""
    convert_script = target_dir / "convert_hf_to_gguf.py"
    quant_bin = target_dir / "build" / "bin" / "llama-quantize"

    if convert_script.is_file() and quant_bin.is_file():
        print(f"✔ Using existing llama.cpp build at {target_dir}")
        return target_dir

    print(f"\n==> Building llama.cpp in {target_dir}...")
    if not target_dir.is_dir():
        subprocess.run(
            ["git", "clone", "--depth", "1", "https://github.com/ggml-org/llama.cpp", str(target_dir)],
            check=True,
        )

    build_dir = target_dir / "build"
    subprocess.run(["cmake", "-S", str(target_dir), "-B", str(build_dir)], check=True)
    subprocess.run(["cmake", "--build", str(build_dir), "-j"], check=True)
    print("✔ llama.cpp built successfully.")
    return target_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Kaggle Merge, GGUF & Deploy Runner")
    parser.add_argument("--base-model", default="Qwen/Qwen3-8B")
    parser.add_argument("--adapter-id", default="nabin2004/AOS-qwen3-8b-narrated-dpo")
    parser.add_argument("--hub-merged-repo", default="nabin2004/AOS-qwen3-8b-narrated-merged")
    parser.add_argument("--hub-gguf-repo", default="nabin2004/AOS-qwen3-8b-narrated-gguf")
    parser.add_argument("--quantize-types", nargs="+", default=["Q4_K_M", "Q8_0"])
    parser.add_argument("--skip-merge", action="store_true")
    parser.add_argument("--skip-gguf", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    args = parser.parse_args()

    setup_kaggle_secrets()
    install_deployment_dependencies()

    workspace = Path("/kaggle/working") if Path("/kaggle/working").is_dir() else QWEN_ROOT
    merged_dir = workspace / "qwen3-8b-narrated-merged"
    gguf_dir = workspace / "qwen3-8b-narrated-gguf"
    llama_cpp_dir = workspace / "llama.cpp"

    if not args.skip_gguf:
        build_llama_cpp(llama_cpp_dir)

    deploy_script = QWEN_ROOT / "deploy_narrated_model.py"
    cmd = [
        sys.executable,
        str(deploy_script),
        "--base-model",
        args.base_model,
        "--adapter-id",
        args.adapter_id,
        "--merged-dir",
        str(merged_dir),
        "--gguf-dir",
        str(gguf_dir),
        "--hub-merged-repo",
        args.hub_merged_repo,
        "--hub-gguf-repo",
        args.hub_gguf_repo,
        "--quantize-types",
        *args.quantize_types,
        "--llama-cpp-dir",
        str(llama_cpp_dir),
        "--device",
        "auto",
    ]

    if args.skip_merge:
        cmd.append("--skip-merge")
    if args.skip_gguf:
        cmd.append("--skip-gguf")
    if args.no_push:
        cmd.append("--no-push")

    print("\n=================================================================")
    print("🚀 Launching Master Deployment Pipeline...")
    print("=================================================================\n")
    subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
