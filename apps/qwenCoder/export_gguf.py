#!/usr/bin/env python3
"""Convert merged Qwen HF checkpoint to GGUF (llama.cpp) and optionally push.

Usage (from apps/qwenCoder):

    export LLAMA_CPP_DIR=~/llama.cpp
    uv run python export_gguf.py \\
      --model-dir ./qwen2.5-coder-7b-manim-merged \\
      --output-dir ./qwen2.5-coder-7b-manim-gguf
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from hub_upload import push_model_folder, require_token
from identity import HUB_GGUF_REPO, OLLAMA_MODEL_TAG

DEFAULT_QUANT = "Q4_K_M"
QWEN_ROOT = Path(__file__).resolve().parent
MODELFILE_TEMPLATE = QWEN_ROOT / "templates" / "Modelfile.qwen2.5-coder-7b-manim"


@dataclass(frozen=True)
class LlamaCppTools:
    llama_cpp_dir: Path
    convert_script: Path
    quantize_binary: Path


def resolve_llama_cpp_tools(llama_cpp_dir: Path) -> LlamaCppTools:
    if not llama_cpp_dir.is_dir():
        raise FileNotFoundError(f"llama.cpp not found: {llama_cpp_dir}")
    convert_script = llama_cpp_dir / "convert_hf_to_gguf.py"
    if not convert_script.is_file():
        raise FileNotFoundError(f"Missing {convert_script}")
    quantize_binary = llama_cpp_dir / "build" / "bin" / "llama-quantize"
    if not quantize_binary.is_file():
        # Windows / alternate layout
        alt = llama_cpp_dir / "build" / "bin" / "Release" / "llama-quantize.exe"
        if alt.is_file():
            quantize_binary = alt
        else:
            raise FileNotFoundError(f"Missing llama-quantize under {llama_cpp_dir}/build")
    return LlamaCppTools(llama_cpp_dir, convert_script, quantize_binary)


def _run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def write_modelfile(output_dir: Path, gguf_filename: str, model_name: str) -> Path:
    if MODELFILE_TEMPLATE.is_file():
        content = MODELFILE_TEMPLATE.read_text(encoding="utf-8").format(
            gguf_file=gguf_filename,
            model_name=model_name,
        )
    else:
        content = f"FROM ./{gguf_filename}\nPARAMETER temperature 0.2\n"
    path = output_dir / "Modelfile"
    path.write_text(content, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-name", default=OLLAMA_MODEL_TAG)
    parser.add_argument("--llama-cpp-dir", type=Path, default=None)
    parser.add_argument("--quantize", default=DEFAULT_QUANT)
    parser.add_argument("--skip-ollama-create", action="store_true")
    parser.add_argument("--push-to-hub", action="store_true")
    parser.add_argument("--hub-repo-id", default=HUB_GGUF_REPO)
    parser.add_argument("--hub-private", action="store_true")
    args = parser.parse_args()

    model_dir = args.model_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    llama_cpp_dir = (
        args.llama_cpp_dir
        or Path(os.environ.get("LLAMA_CPP_DIR", "./llama.cpp"))
    ).expanduser().resolve()

    if not (model_dir / "config.json").is_file():
        print(f"ERROR: no config.json in {model_dir}", file=sys.stderr)
        return 1

    tools = resolve_llama_cpp_tools(llama_cpp_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    f16_path = output_dir / f"{args.model_name}-f16.gguf"
    _run(
        [
            sys.executable,
            str(tools.convert_script),
            str(model_dir),
            "--outfile",
            str(f16_path),
            "--outtype",
            "f16",
        ]
    )

    quant = None if args.quantize.lower() == "none" else args.quantize
    if quant:
        final_name = f"{args.model_name}-{quant}.gguf"
        final_path = output_dir / final_name
        _run([str(tools.quantize_binary), str(f16_path), str(final_path), quant])
    else:
        final_name = f16_path.name
        final_path = f16_path

    modelfile = write_modelfile(output_dir, final_name, args.model_name)
    print(f"Wrote {modelfile}")

    if not args.skip_ollama_create:
        if shutil.which("ollama") is None:
            print("WARNING: ollama not on PATH; skipping create", file=sys.stderr)
        else:
            _run(["ollama", "create", args.model_name, "-f", str(modelfile)])

    if args.push_to_hub:
        token = require_token()
        ignore = ["README.md"]
        if quant:
            ignore.append("*-f16.gguf")
        push_model_folder(
            output_dir,
            args.hub_repo_id,
            token,
            private=args.hub_private,
            ignore_patterns=ignore,
        )

    print(f"GGUF ready: {final_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
