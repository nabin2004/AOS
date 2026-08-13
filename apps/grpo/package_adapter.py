#!/usr/bin/env python3
"""Package a GRPO (or DPO) LoRA: merge → GGUF → optional Hugging Face push.

Reuses apps/qwenCoder merge/export for Qwen, or apps/sft for Gemma.

Usage (from apps/grpo):

    uv run python package_adapter.py --base qwen \\
      --adapter-dir ./grpo_qwen_manim \\
      --push-to-hub

    uv run python package_adapter.py --base gemma \\
      --adapter-dir ./grpo_manim \\
      --model-id google/gemma-4-31B-it
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

GRPO_ROOT = Path(__file__).resolve().parent
APPS = GRPO_ROOT.parent


def _run(cmd: list[str], *, cwd: Path) -> None:
    print(f"$ {' '.join(cmd)}  (cwd={cwd})")
    subprocess.run(cmd, check=True, cwd=cwd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", choices=("qwen", "gemma"), required=True)
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--merged-dir", type=Path, default=None)
    parser.add_argument("--gguf-dir", type=Path, default=None)
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--push-to-hub", action="store_true")
    parser.add_argument("--skip-gguf", action="store_true")
    parser.add_argument("--llama-cpp-dir", type=Path, default=None)
    args = parser.parse_args()

    adapter = args.adapter_dir.expanduser().resolve()
    if not adapter.is_dir():
        print(f"ERROR: adapter not found: {adapter}", file=sys.stderr)
        return 1

    if args.base == "qwen":
        pkg = APPS / "qwenCoder"
        model_id = args.model_id or "Qwen/Qwen2.5-Coder-7B-Instruct"
        merged = (args.merged_dir or GRPO_ROOT / "qwen-grpo-merged").resolve()
        gguf = (args.gguf_dir or GRPO_ROOT / "qwen-grpo-gguf").resolve()
    else:
        pkg = APPS / "sft"
        model_id = args.model_id or "google/gemma-4-31B-it"
        merged = (args.merged_dir or GRPO_ROOT / "gemma-grpo-merged").resolve()
        gguf = (args.gguf_dir or GRPO_ROOT / "gemma-grpo-gguf").resolve()

    merge_cmd = [
        "uv",
        "run",
        "python",
        "merge_adapter.py",
        "--adapter-dir",
        str(adapter),
        "--output-dir",
        str(merged),
        "--model-id",
        model_id,
    ]
    if args.push_to_hub:
        merge_cmd.append("--push-to-hub")
    _run(merge_cmd, cwd=pkg)

    if args.skip_gguf:
        print(f"Merged only: {merged}")
        return 0

    export_cmd = [
        "uv",
        "run",
        "python",
        "export_gguf.py",
        "--model-dir",
        str(merged),
        "--output-dir",
        str(gguf),
        "--skip-ollama-create",
    ]
    if args.llama_cpp_dir:
        export_cmd.extend(["--llama-cpp-dir", str(args.llama_cpp_dir.resolve())])
    if args.push_to_hub:
        export_cmd.append("--push-to-hub")
    _run(export_cmd, cwd=pkg)

    print(f"Packaged:\n  merged={merged}\n  gguf={gguf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
