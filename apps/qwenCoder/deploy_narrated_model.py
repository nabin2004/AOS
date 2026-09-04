#!/usr/bin/env python3
"""Master deployment tool for AOS Qwen3-8B Narrated (DPO Aligned).

Performs:
1. Merge of LoRA adapter (nabin2004/AOS-qwen3-8b-narrated-dpo) into Qwen/Qwen3-8B base LLM.
2. Generation of high-fidelity Model Card with lineage and DPO tags.
3. Push of merged Safetensors model to Hugging Face (nabin2004/AOS-qwen3-8b-narrated-merged).
4. Conversion of merged checkpoint to GGUF format and multi-quantization (Q4_K_M & Q8_0).
5. Generation of Ollama Modelfile and GGUF Model Card.
6. Push of quantized GGUF repository to Hugging Face (nabin2004/AOS-qwen3-8b-narrated-gguf).
7. (Optional) Local Ollama model registration.

Usage:
    uv run python deploy_narrated_model.py
    uv run python deploy_narrated_model.py --no-push
    uv run python deploy_narrated_model.py --skip-merge --quantize-types Q4_K_M
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
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

QWEN_ROOT = Path(__file__).resolve().parent
if str(QWEN_ROOT) not in sys.path:
    sys.path.insert(0, str(QWEN_ROOT))

from hub_upload import push_model_folder, require_token
from identity import (
    HUB_QWEN3_8B_NARRATED_DPO_REPO,
    HUB_QWEN3_8B_NARRATED_GGUF_REPO,
    HUB_QWEN3_8B_NARRATED_MERGED_REPO,
    OLLAMA_QWEN3_8B_NARRATED_TAG,
    QWEN3_8B_MODEL_ID,
    QWEN3_8B_NARRATED_GGUF_OUTPUT_DIR_NAME,
    QWEN3_8B_NARRATED_MERGED_OUTPUT_DIR_NAME,
)

TEMPLATES_DIR = QWEN_ROOT / "templates"
MERGED_CARD_TEMPLATE = TEMPLATES_DIR / "merged_narrated_model_card.md"
GGUF_CARD_TEMPLATE = TEMPLATES_DIR / "gguf_narrated_model_card.md"
MODELFILE_TEMPLATE = TEMPLATES_DIR / "Modelfile.qwen3-8b-narrated"


@dataclass(frozen=True)
class LlamaCppTools:
    llama_cpp_dir: Path
    convert_script: Path
    quantize_binary: Path


def _hub_token() -> str | None:
    return os.environ.get("HF_TOKEN", "").strip() or None


def _run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"\n$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def resolve_adapter(adapter_id_or_path: str, token: str | None) -> str:
    """Resolve adapter to local directory or download from Hugging Face."""
    candidate = Path(adapter_id_or_path).expanduser()
    if candidate.is_dir() and (candidate / "adapter_config.json").is_file():
        print(f"✔ Using local adapter directory: {candidate.resolve()}")
        return str(candidate.resolve())

    print(f"📥 Downloading adapter from Hugging Face Hub: {adapter_id_or_path}...")
    downloaded = snapshot_download(
        repo_id=adapter_id_or_path,
        repo_type="model",
        token=token,
    )
    print(f"✔ Adapter downloaded to {downloaded}")
    return downloaded


def resolve_or_build_llama_cpp(requested_dir: Path | None) -> LlamaCppTools:
    """Find existing llama.cpp tools or auto-clone and build if on Linux/Kaggle."""
    search_dirs: list[Path] = []
    if requested_dir:
        search_dirs.append(requested_dir.expanduser().resolve())
    if os.environ.get("LLAMA_CPP_DIR"):
        search_dirs.append(Path(os.environ["LLAMA_CPP_DIR"]).expanduser().resolve())
    search_dirs.extend(
        [
            Path("./llama.cpp").resolve(),
            QWEN_ROOT / "llama.cpp",
            Path("/kaggle/working/llama.cpp"),
        ]
    )

    for candidate in search_dirs:
        convert_script = candidate / "convert_hf_to_gguf.py"
        quant_bin = candidate / "build" / "bin" / "llama-quantize"
        quant_exe = candidate / "build" / "bin" / "Release" / "llama-quantize.exe"
        if quant_exe.is_file():
            quant_bin = quant_exe

        if convert_script.is_file() and quant_bin.is_file():
            print(f"✔ Found existing llama.cpp at {candidate}")
            return LlamaCppTools(candidate, convert_script, quant_bin)

    target_dir = search_dirs[0] if search_dirs else (QWEN_ROOT / "llama.cpp")

    # If on Linux / Kaggle / POSIX with git and cmake, attempt auto-build
    if sys.platform != "win32" and shutil.which("git") and shutil.which("cmake"):
        print(f"⚙ Auto-building llama.cpp in {target_dir}...")
        if not target_dir.is_dir():
            _run_cmd(["git", "clone", "--depth", "1", "https://github.com/ggml-org/llama.cpp", str(target_dir)])
        build_dir = target_dir / "build"
        _run_cmd(["cmake", "-S", str(target_dir), "-B", str(build_dir)])
        _run_cmd(["cmake", "--build", str(build_dir), "-j"])

        convert_script = target_dir / "convert_hf_to_gguf.py"
        quant_bin = build_dir / "bin" / "llama-quantize"
        if convert_script.is_file() and quant_bin.is_file():
            print("✔ Successfully built llama.cpp tools.")
            return LlamaCppTools(target_dir, convert_script, quant_bin)

    raise FileNotFoundError(
        f"llama.cpp tools not found in {search_dirs}. Please clone and build llama.cpp:\n"
        "  git clone --depth 1 https://github.com/ggml-org/llama.cpp\n"
        "  cmake -S llama.cpp -B llama.cpp/build && cmake --build llama.cpp/build -j\n"
        "Then set LLAMA_CPP_DIR or pass --llama-cpp-dir."
    )


def render_template(template_path: Path, output_path: Path, **kwargs: str) -> None:
    if not template_path.is_file():
        raise FileNotFoundError(f"Missing template: {template_path}")
    raw = template_path.read_text(encoding="utf-8")
    rendered = raw.format(**kwargs)
    output_path.write_text(rendered, encoding="utf-8")
    print(f"✔ Rendered {output_path.name} -> {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", default=QWEN3_8B_MODEL_ID, help="Base foundation model ID")
    parser.add_argument(
        "--adapter-id",
        default=HUB_QWEN3_8B_NARRATED_DPO_REPO,
        help="Local dir or Hugging Face repo ID of DPO LoRA adapter",
    )
    parser.add_argument(
        "--merged-dir",
        type=Path,
        default=QWEN_ROOT / QWEN3_8B_NARRATED_MERGED_OUTPUT_DIR_NAME,
        help="Output directory for merged bf16 weights",
    )
    parser.add_argument(
        "--gguf-dir",
        type=Path,
        default=QWEN_ROOT / QWEN3_8B_NARRATED_GGUF_OUTPUT_DIR_NAME,
        help="Output directory for GGUF models",
    )
    parser.add_argument(
        "--hub-merged-repo",
        default=HUB_QWEN3_8B_NARRATED_MERGED_REPO,
        help="Target HF repo ID for merged weights",
    )
    parser.add_argument(
        "--hub-gguf-repo",
        default=HUB_QWEN3_8B_NARRATED_GGUF_REPO,
        help="Target HF repo ID for GGUF weights",
    )
    parser.add_argument(
        "--quantize-types",
        nargs="+",
        default=["Q4_K_M", "Q8_0"],
        help="Quantization types to generate (e.g. Q4_K_M Q8_0)",
    )
    parser.add_argument(
        "--ollama-tag",
        default=OLLAMA_QWEN3_8B_NARRATED_TAG,
        help="Tag name for local Ollama registration",
    )
    parser.add_argument(
        "--llama-cpp-dir",
        type=Path,
        default=None,
        help="Path to llama.cpp directory",
    )
    parser.add_argument(
        "--device",
        default="auto" if torch.cuda.is_available() else "cpu",
        choices=["auto", "cuda", "cpu"],
        help="Device to use for model merging",
    )
    parser.add_argument("--skip-merge", action="store_true", help="Skip model merging step")
    parser.add_argument("--skip-gguf", action="store_true", help="Skip GGUF conversion & quantization")
    parser.add_argument("--skip-ollama-create", action="store_true", help="Skip local `ollama create`")
    parser.add_argument("--no-push", action="store_true", help="Do not upload repositories to Hugging Face Hub")
    args = parser.parse_args()

    merged_dir = args.merged_dir.expanduser().resolve()
    gguf_dir = args.gguf_dir.expanduser().resolve()
    token = _hub_token()

    print("=================================================================")
    print("🚀 AOS Qwen3-8B Narrated Master Deployment Pipeline")
    print(f"Base LLM:        {args.base_model}")
    print(f"DPO Adapter:     {args.adapter_id}")
    print(f"Merged Repo:     {args.hub_merged_repo}")
    print(f"GGUF Repo:       {args.hub_gguf_repo}")
    print(f"Quantizations:   {args.quantize_types}")
    print(f"Ollama Tag:      {args.ollama_tag}")
    print("=================================================================")

    # -------------------------------------------------------------------------
    # STEP 1: MERGE ADAPTER & BASE LLM
    # -------------------------------------------------------------------------
    if not args.skip_merge:
        print("\n[Step 1/2] Merging DPO Adapter into Full bf16 Weights...")
        resolved_adapter = resolve_adapter(args.adapter_id, token)

        print(f"Loading base {args.base_model} (bf16, device={args.device})...")
        tokenizer = AutoTokenizer.from_pretrained(
            args.base_model, trust_remote_code=True, token=token
        )

        device_map = args.device if args.device != "cuda" else {"": "cuda:0"}
        base = AutoModelForCausalLM.from_pretrained(
            args.base_model,
            torch_dtype=torch.bfloat16,
            device_map=device_map,
            trust_remote_code=True,
            token=token,
        )

        print(f"Attaching LoRA adapter from {resolved_adapter}...")
        model = PeftModel.from_pretrained(base, resolved_adapter, token=token)

        print("Executing merge_and_unload()...")
        model = model.merge_and_unload()

        merged_dir.mkdir(parents=True, exist_ok=True)
        print(f"Saving merged safetensors model to {merged_dir}...")
        model.save_pretrained(str(merged_dir), safe_serialization=True)
        tokenizer.save_pretrained(str(merged_dir))

        # Render Model Card
        render_template(
            MERGED_CARD_TEMPLATE,
            merged_dir / "README.md",
            hub_merged_repo=args.hub_merged_repo,
            hub_gguf_repo=args.hub_gguf_repo,
        )
        print(f"✔ Merged weights ready at {merged_dir}")

        if not args.no_push:
            hub_token = require_token()
            print(f"\nUploading merged model folder to https://huggingface.co/{args.hub_merged_repo}...")
            push_model_folder(merged_dir, args.hub_merged_repo, hub_token)
            print(f"✔ Merged model successfully deployed to Hugging Face!")
    else:
        print("\n⏭ Skipped Step 1 (Model Merging).")

    # -------------------------------------------------------------------------
    # STEP 2: CONVERT TO GGUF & MULTI-QUANTIZE
    # -------------------------------------------------------------------------
    if not args.skip_gguf:
        print("\n[Step 2/2] Converting Merged Model to GGUF...")
        if not (merged_dir / "config.json").is_file():
            print(f"ERROR: Merged model directory {merged_dir} does not contain config.json!", file=sys.stderr)
            return 1

        tools = resolve_or_build_llama_cpp(args.llama_cpp_dir)
        gguf_dir.mkdir(parents=True, exist_ok=True)

        f16_path = gguf_dir / f"{args.ollama_tag}-f16.gguf"
        print(f"\n---> Converting Hugging Face model to F16 GGUF: {f16_path.name}")
        _run_cmd(
            [
                sys.executable,
                str(tools.convert_script),
                str(merged_dir),
                "--outfile",
                str(f16_path),
                "--outtype",
                "f16",
            ]
        )

        for quant in args.quantize_types:
            quant_name = f"{args.ollama_tag}-{quant}.gguf"
            quant_path = gguf_dir / quant_name
            print(f"\n---> Quantizing to {quant}: {quant_name}")
            _run_cmd([str(tools.quantize_binary), str(f16_path), str(quant_path), quant])
            print(f"✔ Created {quant_path} ({quant_path.stat().st_size / 1e9:.2f} GB)")

        # Write Modelfile pointing to primary quant (Q4_K_M if available, else first quant)
        primary_quant = "Q4_K_M" if "Q4_K_M" in args.quantize_types else args.quantize_types[0]
        render_template(
            MODELFILE_TEMPLATE,
            gguf_dir / "Modelfile",
            gguf_file=f"{args.ollama_tag}-{primary_quant}.gguf",
        )

        # Write GGUF Model Card
        render_template(
            GGUF_CARD_TEMPLATE,
            gguf_dir / "README.md",
            hub_merged_repo=args.hub_merged_repo,
            hub_gguf_repo=args.hub_gguf_repo,
            ollama_tag=args.ollama_tag,
        )

        # Optional Ollama create
        if not args.skip_ollama_create:
            if shutil.which("ollama") is not None:
                print(f"\n---> Registering with local Ollama: {args.ollama_tag}...")
                _run_cmd(["ollama", "create", args.ollama_tag, "-f", str(gguf_dir / "Modelfile")])
                print(f"✔ Ollama model '{args.ollama_tag}' created successfully!")
            else:
                print("\nNotice: 'ollama' binary not found on PATH; skipping local model registration.")

        # Push to Hub
        if not args.no_push:
            hub_token = require_token()
            print(f"\nUploading GGUF models to https://huggingface.co/{args.hub_gguf_repo}...")
            push_model_folder(
                gguf_dir,
                args.hub_gguf_repo,
                hub_token,
                ignore_patterns=["*-f16.gguf"],
            )
            print(f"✔ GGUF repository successfully deployed to Hugging Face!")

        # Clean up temporary large f16 intermediate GGUF to conserve disk space
        if f16_path.is_file():
            print(f"\nCleaning up intermediate F16 GGUF: {f16_path.name}")
            f16_path.unlink()

        print("\n✔ Step 2 Complete: GGUF models ready.")
    else:
        print("\n⏭ Skipped Step 2 (GGUF Conversion).")

    print("\n=================================================================")
    print("🎉 Master Deployment Finished Successfully!")
    if not args.no_push:
        print(f"Merged Safetensors: https://huggingface.co/{args.hub_merged_repo}")
        print(f"Quantized GGUF:     https://huggingface.co/{args.hub_gguf_repo}")
    print("=================================================================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
