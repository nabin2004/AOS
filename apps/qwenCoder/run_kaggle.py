#!/usr/bin/env python3
"""Super Simple One-Click Kaggle Runner for Qwen3-8B Pipeline.

Features:
1. Auto-retrieves HF_TOKEN and WANDB_API_KEY from Kaggle UserSecretsClient.
2. Checks PyTorch CUDA compatibility before reinstalling (saves 2.5GB download / ~3 mins).
3. Auto-curates 5,400-sample dataset (nabin2004/manim-aos-5k400) if missing or requested.
4. Executes QLoRA SFT, adapter merging, GGUF multi-quantization (Q4_K_M & Q8_0), and HuggingFace uploads.

Usage in Kaggle Notebook:
    !python3 apps/qwenCoder/run_kaggle.py
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
    """Retrieve HF_TOKEN and WANDB_API_KEY from Kaggle UserSecretsClient if not set."""
    if "HF_TOKEN" not in os.environ:
        try:
            from kaggle_secrets import UserSecretsClient  # type: ignore

            secrets = UserSecretsClient()
            token = secrets.get_secret("HF_TOKEN")
            if token:
                os.environ["HF_TOKEN"] = token
                print("✔ Successfully retrieved HF_TOKEN from Kaggle UserSecrets.")
        except Exception as exc:
            print(f"Notice: Could not auto-fetch HF_TOKEN from Kaggle secrets: {exc}")

    if "WANDB_API_KEY" not in os.environ:
        try:
            from kaggle_secrets import UserSecretsClient  # type: ignore

            secrets = UserSecretsClient()
            wandb_key = secrets.get_secret("WANDB_API_KEY")
            if wandb_key:
                os.environ["WANDB_API_KEY"] = wandb_key
                print("✔ Successfully retrieved WANDB_API_KEY from Kaggle UserSecrets.")
        except Exception:
            pass


def is_cuda_working() -> bool:
    """Test whether system PyTorch can perform CUDA matrix multiplication."""
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        x = torch.randn(64, 64, device="cuda")
        _ = x @ x
        torch.cuda.synchronize()
        return True
    except Exception:
        return False


def setup_environment(force_reinstall_torch: bool = False) -> None:
    """Install dependencies into Kaggle system Python without unnecessary torch downloads."""
    python_exe = sys.executable

    if not force_reinstall_torch and is_cuda_working():
        import torch
        print(f"✔ PyTorch {torch.__version__} with CUDA ({torch.version.cuda}) is working. Skipping PyTorch re-installation!")
    else:
        print("==> Pinning system torch 2.7.1+cu118 for Kaggle P100 sm_60...")
        subprocess.run(
            [python_exe, "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"],
            check=False,
        )
        subprocess.run(
            [
                python_exe,
                "-m",
                "pip",
                "install",
                "torch==2.7.1",
                "torchvision==0.22.1",
                "torchaudio==2.7.1",
                "--index-url",
                "https://download.pytorch.org/whl/cu118",
            ],
            check=True,
        )

    print("==> Installing SFT & quantization dependencies...")
    deps = [
        "accelerate>=1.0.0",
        "bitsandbytes>=0.45.0",
        "datasets>=5.0.0",
        "huggingface-hub>=0.27.0",
        "peft>=0.19.1",
        "transformers>=4.51.0",
        "trl>=0.19.0",
        "wandb>=0.19.0",
        "wrapt",
    ]
    subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([python_exe, "-m", "pip", "install"] + deps, check=True)

    # Kaggle pre-installs incompatible torchao==0.10.0 which breaks PEFT adapter loading/merging (>0.16.0 required)
    subprocess.run([python_exe, "-m", "pip", "uninstall", "-y", "torchao"], check=False)

    print("==> Installing qwenCoder package in editable mode (--no-deps)...")
    subprocess.run([python_exe, "-m", "pip", "install", "-e", str(QWEN_ROOT), "--no-deps"], check=True)


def ensure_llama_cpp(target_dir: Path) -> Path:
    """Clone and compile llama.cpp if not already present."""
    convert_script = target_dir / "convert_hf_to_gguf.py"
    quant_bin = target_dir / "build" / "bin" / "llama-quantize"

    if convert_script.is_file() and quant_bin.is_file():
        print(f"✔ Using existing llama.cpp build at {target_dir}")
        return target_dir

    print(f"\n==> Building llama.cpp in {target_dir} for GGUF quantization...")
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


from identity import (
    HUB_QWEN3_8B_DATASET_REPO,
    HUB_QWEN3_8B_GGUF_REPO,
    HUB_QWEN3_8B_MERGED_REPO,
    HUB_QWEN3_8B_SFT_REPO,
    QWEN3_8B_MODEL_ID,
)


def ensure_dataset(dataset_repo: str, force_curate: bool = False) -> None:
    """Ensure dataset is present or curate manually if requested."""
    if force_curate:
        print("\n==> Force curating local 5.4k dataset...")
        cmd = [sys.executable, str(QWEN_ROOT / "curate_sft_5k_400.py")]
        if os.environ.get("HF_TOKEN"):
            cmd.extend(["--push", "--repo-id", "nabin2004/manim-aos-5k400"])
        subprocess.run(cmd, check=True)
    else:
        print(f"\n✔ Using Hub dataset: {dataset_repo} (will be loaded directly by Hugging Face Datasets)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Super Simple Kaggle One-Click Qwen3-8B Pipeline")
    parser.add_argument("--model-id", default=QWEN3_8B_MODEL_ID, help="Base HF model ID")
    parser.add_argument("--dataset-repo", default=HUB_QWEN3_8B_DATASET_REPO, help="Dataset repo ID")
    parser.add_argument("--hub-adapter-repo", default=HUB_QWEN3_8B_SFT_REPO, help="HF repo for adapter")
    parser.add_argument("--hub-merged-repo", default=HUB_QWEN3_8B_MERGED_REPO, help="HF repo for merged model")
    parser.add_argument("--hub-gguf-repo", default=HUB_QWEN3_8B_GGUF_REPO, help="HF repo for quantized GGUF")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs (default: 3)")
    parser.add_argument("--save-steps", type=int, default=50, help="Checkpoint save steps (default: 50)")
    parser.add_argument("--seq-len", type=int, default=4096, help="Sequence length (default: 4096)")
    parser.add_argument("--max-samples", type=int, default=0, help="Max samples to train (0 = full dataset)")
    parser.add_argument("--val-split", type=float, default=0.0, help="Validation split ratio e.g. 0.05")
    parser.add_argument("--curate", action="store_true", help="Force local 5k dataset curation before training")
    parser.add_argument("--force-reinstall-torch", action="store_true", help="Force reinstall PyTorch cu118")
    parser.add_argument("--resume", action="store_true", help="Resume from an existing checkpoint instead of fresh start")
    parser.add_argument("--skip-train", action="store_true", help="Skip training step")
    parser.add_argument("--skip-merge", action="store_true", help="Skip merge step")
    parser.add_argument("--skip-gguf", action="store_true", help="Skip GGUF quantization step")
    parser.add_argument("--no-push", action="store_true", help="Dry run: skip pushing to Hugging Face Hub")
    args = parser.parse_args()

    print("=================================================================")
    print("🚀 Starting Simple Kaggle Qwen3-8B Pipeline")
    print(f"   Model:        {args.model_id}")
    print(f"   Dataset:      {args.dataset_repo}")
    print(f"   Epochs:       {args.epochs}")
    print(f"   Seq Len:      {args.seq_len}")
    print(f"   Save Steps:   {args.save_steps}")
    print(f"   Fresh Run:    {not args.resume}")
    print(f"   Adapter Hub:  {args.hub_adapter_repo}")
    print(f"   Merged Hub:   {args.hub_merged_repo}")
    print(f"   GGUF Hub:     {args.hub_gguf_repo}")
    print("=================================================================")

    setup_kaggle_secrets()

    if not os.environ.get("HF_TOKEN") and not args.no_push:
        print("WARNING: HF_TOKEN is not set. Hugging Face uploads will fail unless HF_TOKEN is exported or in Kaggle Secrets.")

    setup_environment(force_reinstall_torch=args.force_reinstall_torch)

    ensure_dataset(dataset_repo=args.dataset_repo, force_curate=args.curate)

    if not args.resume and not args.skip_train:
        local_adapter_dir = QWEN_ROOT / "qwen3-8b-manim-ft"
        if local_adapter_dir.exists():
            print(f"\n==> Ensuring fresh start: cleaning stale checkpoint directory {local_adapter_dir}...")
            import shutil
            shutil.rmtree(local_adapter_dir, ignore_errors=True)

    llama_dir = None
    if not args.skip_gguf:
        target_llama = Path("/kaggle/working/llama.cpp") if Path("/kaggle/working").is_dir() else (REPO_ROOT / "llama.cpp")
        llama_dir = ensure_llama_cpp(target_llama)
        os.environ["LLAMA_CPP_DIR"] = str(llama_dir)

    print("\n==> Launching Master Qwen3-8B End-to-End Pipeline...")
    e2e_cmd = [
        sys.executable,
        str(QWEN_ROOT / "run_e2e_qwen3.py"),
        "--kaggle",
        "--model-id",
        args.model_id,
        "--dataset-repo",
        args.dataset_repo,
        "--hub-adapter-repo",
        args.hub_adapter_repo,
        "--hub-merged-repo",
        args.hub_merged_repo,
        "--hub-gguf-repo",
        args.hub_gguf_repo,
        "--epochs",
        str(args.epochs),
        "--save-steps",
        str(args.save_steps),
        "--seq-len",
        str(args.seq_len),
        "--max-samples",
        str(args.max_samples),
        "--val-split",
        str(args.val_split),
    ]
    if llama_dir:
        e2e_cmd.extend(["--llama-cpp-dir", str(llama_dir)])
    if args.resume:
        e2e_cmd.append("--resume")
    if not args.no_push:
        e2e_cmd.append("--push-to-hub")
    if args.skip_train:
        e2e_cmd.append("--skip-train")
    if args.skip_merge:
        e2e_cmd.append("--skip-merge")
    if args.skip_gguf:
        e2e_cmd.append("--skip-gguf")

    subprocess.run(e2e_cmd, check=True)

    print("\n=================================================================")
    print("🎉 Kaggle Qwen3-8B Pipeline Completed Successfully!")
    print("=================================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
