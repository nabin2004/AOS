#!/usr/bin/env python3
"""One-Click Kaggle Runner for GRPO Mathematical Animation RL Pipeline.

Supports:
- Dual NVIDIA T4 (2x 16GB = 32GB VRAM): Auto-activates multi-GPU sampling & 4-bit QLoRA.
- Single NVIDIA Tesla P100 (16GB VRAM): Auto-activates conservative batching.

Pipeline Steps:
1. Auto-retrieves HF_TOKEN and WANDB_API_KEY from Kaggle UserSecrets.
2. Configures PyTorch CUDA memory management (expandable segments).
3. Installs runtime dependencies without redundant torch reinstalls.
4. Loads Manim-grpo-dataset-200 problem bundles and reward metadata.
5. Executes GRPO training with multi-stage reward evaluation (lexical + live OpenCLIP vision + VCER + coverage).
6. Packages and uploads the trained GRPO LoRA adapter to Hugging Face Hub.

Usage in Kaggle Notebook:
    !python3 apps/grpo/run_kaggle_grpo.py --push-to-hub
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

GRPO_ROOT = Path(__file__).resolve().parent
REPO_ROOT = GRPO_ROOT.parent.parent

DEFAULT_BASE_MODEL = "Qwen/Qwen3-8B"
DEFAULT_INIT_ADAPTER = "nabin2004/AOS-qwen3-8b-narrated-dpo"
DEFAULT_DATASET_REPO = "nabin2004/Manim-grpo-dataset-200"
DEFAULT_HUB_OUTPUT_REPO = "nabin2004/AOS-qwen3-8b-grpo"


def setup_kaggle_secrets() -> None:
    """Retrieve HF_TOKEN and WANDB_API_KEY from Kaggle UserSecretsClient if available."""
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

    if os.environ.get("WANDB_API_KEY"):
        try:
            import wandb
            wandb.login(key=os.environ["WANDB_API_KEY"], relogin=True)
            print("✔ Authenticated Weights & Biases (W&B) session.")
        except Exception as e:
            print(f"Notice: W&B login encountered: {e}")


def detect_gpu_hardware() -> tuple[int, str]:
    """Detect available CUDA GPUs and return device count and primary device name."""
    try:
        import torch

        if not torch.cuda.is_available():
            print("ERROR: No CUDA GPU detected!", file=sys.stderr)
            sys.exit(1)

        count = torch.cuda.device_count()
        name = torch.cuda.get_device_name(0)
        print(f"✔ Detected {count} GPU(s): {name}")
        for i in range(count):
            mem_gb = torch.cuda.get_device_properties(i).total_memory / (1024**3)
            print(f"   GPU {i}: {torch.cuda.get_device_name(i)} ({mem_gb:.1f} GB VRAM)")
        return count, name
    except Exception as e:
        print(f"Notice: GPU detection encountered: {e}")
        return 1, "Unknown GPU"


def setup_environment() -> None:
    """Install required packages in Kaggle system Python."""
    python_exe = sys.executable
    required_packages = [
        "trl>=0.14.0",
        "peft>=0.14.0",
        "bitsandbytes>=0.45.0",
        "datasets>=3.0.0",
        "accelerate>=1.2.0",
        "huggingface-hub>=0.28.0",
        "open-clip-torch>=2.24.0",
        "wandb",
    ]

    print(f"Checking and installing GRPO dependencies...")
    cmd = [python_exe, "-m", "pip", "install", "-q"] + required_packages
    subprocess.check_call(cmd)
    print("✔ GRPO dependencies installed.")


def run_grpo_training(
    base_model: str,
    sft_lora: str,
    output_dir: Path,
    dataset_repo: str,
    dual_gpu: bool,
    smoke: bool,
    max_steps: int | None,
    render: bool,
    report_to: str,
    run_name: str,
) -> None:
    """Execute GRPO training via subprocess or direct module invocation."""
    python_exe = sys.executable
    run_script = GRPO_ROOT / "run.py"

    cmd = [
        python_exe,
        str(run_script),
        "--base",
        "qwen",
        "--base-model",
        base_model,
        "--sft-lora",
        sft_lora,
        "--output-dir",
        str(output_dir),
        "--report-to",
        report_to,
        "--run-name",
        run_name,
    ]

    if dual_gpu:
        cmd.append("--dual-t4")
    else:
        cmd.append("--p100")

    if smoke:
        cmd.append("--smoke")

    if max_steps is not None:
        cmd.extend(["--max-steps", str(max_steps)])

    if render:
        cmd.append("--render")
    else:
        cmd.append("--no-render")

    print(f"\n🚀 Launching GRPO training command:")
    print(" ".join(cmd))
    subprocess.check_call(cmd, cwd=str(GRPO_ROOT))


def push_adapter_to_hub(adapter_dir: Path, repo_id: str) -> None:
    """Push the trained GRPO LoRA adapter to Hugging Face Hub."""
    try:
        from huggingface_hub import HfApi, get_token

        token = os.environ.get("HF_TOKEN") or (get_token() if get_token else None)
        if not token:
            print("Notice: No HF_TOKEN found. Skipping push to Hugging Face Hub.")
            return

        api = HfApi(token=token)
        print(f"\nUploading GRPO LoRA adapter: {adapter_dir} -> {repo_id}")
        api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True, token=token)
        api.upload_folder(
            folder_path=str(adapter_dir),
            repo_id=repo_id,
            repo_type="model",
            token=token,
        )
        print(f"✔ Successfully published GRPO model to: https://huggingface.co/{repo_id}")
    except Exception as e:
        print(f"Failed to push GRPO adapter to Hub: {e}", file=sys.stderr)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kaggle End-to-End GRPO Pipeline Runner")
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL, help="Base policy model ID")
    parser.add_argument("--sft-lora", default=DEFAULT_INIT_ADAPTER, help="Initial SFT/DPO adapter path or HF repo ID")
    parser.add_argument("--dataset-repo", default=DEFAULT_DATASET_REPO, help="Dataset repo on HF Hub")
    parser.add_argument("--output-dir", default=str(GRPO_ROOT / "grpo_qwen_manim"), help="Output adapter directory")
    parser.add_argument("--hub-repo", default=DEFAULT_HUB_OUTPUT_REPO, help="Hugging Face repo ID for final GRPO adapter")
    parser.add_argument("--push-to-hub", action="store_true", help="Push trained adapter to Hugging Face Hub")
    parser.add_argument("--smoke", action="store_true", help="Run a single-step smoke test")
    parser.add_argument("--max-steps", type=int, default=None, help="Max GRPO optimization steps")
    parser.add_argument("--render", action="store_true", help="Enable live Manim rendering & OpenCLIP visual reward")
    parser.add_argument("--report-to", default="wandb", help="Logging backend ('wandb' or 'none')")
    parser.add_argument("--run-name", default="qwen3-8b-manim-grpo-kaggle", help="Run name for W&B logging")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    print("=" * 70)
    print("  ManiBench-GRPO End-to-End Kaggle Runner")
    print("=" * 70)

    # 1. Setup Kaggle secrets
    setup_kaggle_secrets()

    # 2. Memory optimizations
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    # 3. Detect GPU
    gpu_count, gpu_name = detect_gpu_hardware()
    dual_gpu = gpu_count >= 2

    # 4. Setup dependencies
    setup_environment()

    # 5. Resolve initial adapter (download from HF if remote repo ID)
    sft_lora = args.sft_lora
    if not Path(sft_lora).exists():
        try:
            from huggingface_hub import snapshot_download

            print(f"Downloading base adapter from Hugging Face Hub: {sft_lora}...")
            token = os.environ.get("HF_TOKEN")
            downloaded_dir = snapshot_download(repo_id=sft_lora, token=token)
            sft_lora = downloaded_dir
            print(f"✔ Downloaded adapter to: {sft_lora}")
        except Exception as e:
            print(f"Notice: Using raw adapter identifier '{sft_lora}' ({e})")

    # 6. Execute GRPO Training
    output_path = Path(args.output_dir)
    run_grpo_training(
        base_model=args.base_model,
        sft_lora=sft_lora,
        output_dir=output_path,
        dataset_repo=args.dataset_repo,
        dual_gpu=dual_gpu,
        smoke=args.smoke,
        max_steps=args.max_steps,
        render=args.render,
        report_to=args.report_to,
        run_name=args.run_name,
    )

    # 7. Push to Hugging Face Hub if requested
    if args.push_to_hub and output_path.exists():
        push_adapter_to_hub(output_path, repo_id=args.hub_repo)

    print("\n🎉 GRPO Pipeline execution completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
