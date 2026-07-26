#!/usr/bin/env python3
"""Convert a merged Hugging Face Gemma 4 checkpoint to GGUF for Ollama.

Run after merge_adapter.py. Requires a local llama.cpp build with Gemma 4
support (April 2026+) and Ollama 0.30+ to serve the result.

Usage (from apps/sft):

    export LLAMA_CPP_DIR=~/llama.cpp
    uv run python export_gguf.py \\
      --model-dir ./gemma4-manim-merged \\
      --output-dir ./gemma4-manim-gguf

    export HF_TOKEN=hf_...
    uv run python export_gguf.py \\
      --model-dir ./gemma4-manim-merged \\
      --output-dir ./gemma4-manim-gguf \\
      --push-to-hub
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

SFT_ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL_NAME = "aos-gemma4-manim"
DEFAULT_QUANT = "Q4_K_M"
DEFAULT_HUB_REPO_ID = "nabin2004/AOS-gemma4-manim-gguf"
DEFAULT_LLAMA_CPP_DIR = Path("./llama.cpp")
MODELFILE_TEMPLATE = SFT_ROOT / "templates" / "Modelfile.gemma4-manim"
GGUF_MODEL_CARD = SFT_ROOT / "gguf_model_card.md"


@dataclass(frozen=True)
class LlamaCppTools:
    llama_cpp_dir: Path
    convert_script: Path
    quantize_binary: Path


@dataclass(frozen=True)
class ExportConfig:
    model_dir: Path
    output_dir: Path
    model_name: str
    llama_cpp_dir: Path
    quantize: str | None
    skip_ollama_create: bool
    push_to_hub: bool
    hub_repo_id: str
    hub_private: bool
    hub_revision: str | None
    upload_f16: bool


def validate_merged_model(model_dir: Path) -> None:
    if not model_dir.is_dir():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")
    if not (model_dir / "config.json").is_file():
        raise FileNotFoundError(f"No config.json in {model_dir}")
    if not any(model_dir.glob("*.safetensors")):
        raise FileNotFoundError(
            f"No *.safetensors weights in {model_dir} — run merge_adapter.py first"
        )


def resolve_llama_cpp_tools(llama_cpp_dir: Path) -> LlamaCppTools:
    if not llama_cpp_dir.is_dir():
        raise FileNotFoundError(
            f"llama.cpp directory not found: {llama_cpp_dir}\n"
            "Clone and build it:\n"
            "  git clone https://github.com/ggml-org/llama.cpp\n"
            "  cd llama.cpp && cmake -B build && cmake --build build -j\n"
            "Then set LLAMA_CPP_DIR or pass --llama-cpp-dir."
        )

    convert_script = llama_cpp_dir / "convert_hf_to_gguf.py"
    if not convert_script.is_file():
        raise FileNotFoundError(f"Missing convert script: {convert_script}")

    quantize_binary = llama_cpp_dir / "build" / "bin" / "llama-quantize"
    if not quantize_binary.is_file():
        raise FileNotFoundError(
            f"Missing llama-quantize binary: {quantize_binary}\n"
            "Build llama.cpp first:\n"
            "  cd llama.cpp && cmake -B build && cmake --build build -j"
        )

    return LlamaCppTools(
        llama_cpp_dir=llama_cpp_dir,
        convert_script=convert_script,
        quantize_binary=quantize_binary,
    )


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=cwd)


def convert_hf_to_gguf(tools: LlamaCppTools, model_dir: Path, outfile: Path) -> Path:
    outfile.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            sys.executable,
            str(tools.convert_script),
            str(model_dir),
            "--outfile",
            str(outfile),
            "--outtype",
            "f16",
        ]
    )
    if not outfile.is_file():
        raise RuntimeError(f"Conversion finished but GGUF not found: {outfile}")
    return outfile


def quantize_gguf(tools: LlamaCppTools, src: Path, dst: Path, quant: str) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    _run([str(tools.quantize_binary), str(src), str(dst), quant])
    if not dst.is_file():
        raise RuntimeError(f"Quantization finished but GGUF not found: {dst}")
    return dst


def write_modelfile(
    output_dir: Path,
    gguf_filename: str,
    model_name: str,
) -> Path:
    if not MODELFILE_TEMPLATE.is_file():
        raise FileNotFoundError(f"Modelfile template not found: {MODELFILE_TEMPLATE}")

    template = MODELFILE_TEMPLATE.read_text(encoding="utf-8")
    content = template.format(gguf_file=gguf_filename, model_name=model_name)
    modelfile = output_dir / "Modelfile"
    modelfile.write_text(content, encoding="utf-8")
    return modelfile


def register_with_ollama(modelfile: Path, model_name: str) -> None:
    if shutil.which("ollama") is None:
        raise FileNotFoundError(
            "ollama not found on PATH — install Ollama 0.30+ or pass --skip-ollama-create"
        )
    _run(["ollama", "create", model_name, "-f", str(modelfile)])


def _hub_ignore_patterns(config: ExportConfig) -> list[str]:
    patterns = ["README.md"]
    if config.quantize and not config.upload_f16:
        patterns.append("*-f16.gguf")
    return patterns


def export_gguf(config: ExportConfig) -> Path:
    validate_merged_model(config.model_dir)
    tools = resolve_llama_cpp_tools(config.llama_cpp_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    f16_path = config.output_dir / f"{config.model_name}-f16.gguf"
    print(f"Converting {config.model_dir} to F16 GGUF...")
    convert_hf_to_gguf(tools, config.model_dir, f16_path)

    if config.quantize:
        final_name = f"{config.model_name}-{config.quantize}.gguf"
        final_path = config.output_dir / final_name
        print(f"Quantizing to {config.quantize}...")
        quantize_gguf(tools, f16_path, final_path, config.quantize)
    else:
        final_name = f16_path.name
        final_path = f16_path

    modelfile = write_modelfile(config.output_dir, final_name, config.model_name)
    print(f"Wrote {modelfile}")

    if config.skip_ollama_create:
        print("\nNext steps:")
        print(f"  ollama create {config.model_name} -f {modelfile}")
        print(f"  ollama run {config.model_name}")
    else:
        print(f"Registering Ollama model '{config.model_name}'...")
        register_with_ollama(modelfile, config.model_name)
        print(f"\nDone. Run: ollama run {config.model_name}")

    if config.push_to_hub:
        token = require_token()
        push_model_folder(
            config.output_dir,
            config.hub_repo_id,
            token,
            readme=GGUF_MODEL_CARD,
            private=config.hub_private,
            revision=config.hub_revision,
            ignore_patterns=_hub_ignore_patterns(config),
        )

    print("\nOpenAI-compatible API (Ollama):")
    print("  base_url = http://localhost:11434/v1")
    print(f"  model    = {config.model_name}")
    return final_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-dir",
        type=Path,
        required=True,
        help="Merged HF checkpoint from merge_adapter.py",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for GGUF files and Modelfile",
    )
    parser.add_argument(
        "--model-name",
        default=DEFAULT_MODEL_NAME,
        help=f"Ollama model tag (default: {DEFAULT_MODEL_NAME})",
    )
    parser.add_argument(
        "--llama-cpp-dir",
        type=Path,
        default=None,
        help="Path to llama.cpp clone (default: $LLAMA_CPP_DIR or ./llama.cpp)",
    )
    parser.add_argument(
        "--quantize",
        default=DEFAULT_QUANT,
        help=f"Quantization type (default: {DEFAULT_QUANT}); use 'none' to keep F16 only",
    )
    parser.add_argument(
        "--skip-ollama-create",
        action="store_true",
        help="Only write GGUF + Modelfile; do not run ollama create",
    )
    parser.add_argument(
        "--push-to-hub",
        action="store_true",
        help="Upload GGUF artifacts to Hugging Face Hub after export",
    )
    parser.add_argument(
        "--hub-repo-id",
        default=DEFAULT_HUB_REPO_ID,
        help=f"HF model repo id (default: {DEFAULT_HUB_REPO_ID})",
    )
    parser.add_argument(
        "--hub-private",
        action="store_true",
        help="Create/upload as a private model repo",
    )
    parser.add_argument(
        "--hub-revision",
        default=None,
        help="Optional branch or tag name for the Hub upload",
    )
    parser.add_argument(
        "--upload-f16",
        action="store_true",
        help="Include F16 intermediate GGUF in Hub upload (large; default skips it)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    llama_cpp_dir = (
        (
            args.llama_cpp_dir
            or Path(os.environ.get("LLAMA_CPP_DIR", DEFAULT_LLAMA_CPP_DIR))
        )
        .expanduser()
        .resolve()
    )
    quantize = None if args.quantize.lower() == "none" else args.quantize

    config = ExportConfig(
        model_dir=args.model_dir.resolve(),
        output_dir=args.output_dir.resolve(),
        model_name=args.model_name,
        llama_cpp_dir=llama_cpp_dir,
        quantize=quantize,
        skip_ollama_create=args.skip_ollama_create,
        push_to_hub=args.push_to_hub,
        hub_repo_id=args.hub_repo_id,
        hub_private=args.hub_private,
        hub_revision=args.hub_revision,
        upload_f16=args.upload_f16,
    )

    try:
        export_gguf(config)
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            return exc.returncode or 1
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
