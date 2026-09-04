#!/usr/bin/env python3
"""Convert nabin2004/qwen2.5-coder-7b-manim-merged to GGUF (Q4_K_M, Q8_0) and deploy.

Performs:
1. Downloads / snapshots nabin2004/qwen2.5-coder-7b-manim-merged.
2. Converts Safetensors checkpoint to F16 GGUF using convert_hf_to_gguf.py.
3. Quantizes to Q4_K_M and Q8_0 with llama-quantize.
4. Generates Modelfile and GGUF documentation.
5. Uploads to:
   - nabin2004/qwen2.5-coder-7b-manim-merged (enabling 1-click Ollama pull)
   - nabin2004/AOS-qwen2.5-coder-7b-manim-gguf (dedicated GGUF repository)
6. Registers locally in Ollama as 'aos-qwen2.5-coder-7b-manim'.

Usage:
    uv run python deploy_qwen25_coder_gguf.py
    uv run python deploy_qwen25_coder_gguf.py --no-push
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from huggingface_hub import HfApi, get_token, snapshot_download

QWEN_ROOT = Path(__file__).resolve().parent
DEFAULT_MERGED_REPO = "nabin2004/qwen2.5-coder-7b-manim-merged"
DEFAULT_GGUF_REPO = "nabin2004/AOS-qwen2.5-coder-7b-manim-gguf"
DEFAULT_MODEL_NAME = "qwen2.5-coder-7b-manim"
DEFAULT_OLLAMA_TAG = "aos-qwen2.5-coder-7b-manim"


def resolve_tools() -> tuple[Path, Path]:
    convert_candidates = [
        QWEN_ROOT / "llama_bin" / "convert_hf_to_gguf.py",
        QWEN_ROOT / "llama_repo" / "convert_hf_to_gguf.py",
        Path("./llama.cpp/convert_hf_to_gguf.py").resolve(),
    ]
    convert_py = next((p for p in convert_candidates if p.is_file()), None)
    if not convert_py:
        raise FileNotFoundError(f"Missing convert_hf_to_gguf.py in {convert_candidates}")

    quant_candidates = [
        QWEN_ROOT / "llama_bin" / "llama-quantize.exe",
        QWEN_ROOT / "llama_bin" / "llama-quantize",
        QWEN_ROOT / "llama_repo" / "build" / "bin" / "Release" / "llama-quantize.exe",
        QWEN_ROOT / "llama_repo" / "build" / "bin" / "llama-quantize",
    ]
    quant_exe = next((p for p in quant_candidates if p.is_file()), None)
    if not quant_exe:
        raise FileNotFoundError(f"Missing llama-quantize binary in {quant_candidates}")

    return convert_py, quant_exe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merged-repo", default=DEFAULT_MERGED_REPO, help="HF repo ID of merged safetensors model")
    parser.add_argument("--gguf-repo", default=DEFAULT_GGUF_REPO, help="Target dedicated HF GGUF repo ID")
    parser.add_argument("--output-dir", type=Path, default=QWEN_ROOT / "qwen2.5-coder-7b-manim-gguf", help="Output dir for GGUF")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME, help="Prefix for GGUF filenames")
    parser.add_argument("--ollama-tag", default=DEFAULT_OLLAMA_TAG, help="Tag for local Ollama registration")
    parser.add_argument("--quantize-types", nargs="+", default=["Q4_K_M", "Q8_0"], help="Quantization types")
    parser.add_argument("--no-push", action="store_true", help="Do not upload to Hugging Face")
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN") or get_token()
    api = HfApi(token=token)

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=================================================================")
    print("🚀 AOS Qwen2.5-Coder-7B GGUF Conversion & Deployment Pipeline")
    print(f"Source Model:    {args.merged_repo}")
    print(f"Target GGUF:     {args.gguf_repo}")
    print(f"Output Dir:      {output_dir}")
    print(f"Quantizations:   {args.quantize_types}")
    print(f"Ollama Tag:      {args.ollama_tag}")
    print("=================================================================")

    # 1. Download/snapshot source model
    print(f"\n[Step 1/4] Fetching source model {args.merged_repo}...")
    local_source = snapshot_download(
        repo_id=args.merged_repo,
        token=token,
    )
    print(f"✔ Source model available at: {local_source}")

    # 2. Resolve conversion tools
    convert_py, quant_exe = resolve_tools()
    print(f"✔ Using conversion script: {convert_py}")
    print(f"✔ Using quantize binary:    {quant_exe}")

    # 3. Convert to F16 GGUF
    f16_gguf = output_dir / f"{args.model_name}-f16.gguf"
    if not any((output_dir / f"{args.model_name}-{q}.gguf").is_file() for q in args.quantize_types):
        if not f16_gguf.is_file():
            print(f"\n[Step 2/4] Converting Safetensors to F16 GGUF: {f16_gguf.name}...")
            subprocess.run(
                [
                    sys.executable,
                    str(convert_py),
                    local_source,
                    "--outfile",
                    str(f16_gguf),
                    "--outtype",
                    "f16",
                ],
                check=True,
            )
            print(f"✔ Created F16 GGUF ({f16_gguf.stat().st_size / 1e9:.2f} GB)")

        # 4. Multi-Quantization
        print(f"\n[Step 3/4] Multi-quantizing to {args.quantize_types}...")
        for q in args.quantize_types:
            q_file = output_dir / f"{args.model_name}-{q}.gguf"
            if not q_file.is_file():
                print(f"---> Quantizing {q}: {q_file.name}...")
                subprocess.run([str(quant_exe), str(f16_gguf), str(q_file), q], check=True)
                print(f"✔ Created {q_file.name} ({q_file.stat().st_size / 1e9:.2f} GB)")
            else:
                print(f"✔ {q_file.name} already exists ({q_file.stat().st_size / 1e9:.2f} GB)")

        # Clean up temporary F16 GGUF
        if f16_gguf.is_file():
            print(f"Removing intermediate F16 file: {f16_gguf.name}")
            f16_gguf.unlink()
    else:
        print(f"\n✔ Quantized files already exist in {output_dir}. Skipping conversion.")

    # 5. Write Modelfile
    primary_quant = "Q4_K_M" if "Q4_K_M" in args.quantize_types else args.quantize_types[0]
    primary_gguf_name = f"{args.model_name}-{primary_quant}.gguf"

    modelfile_content = f"""FROM ./{primary_gguf_name}

TEMPLATE \"\"\"{{{{ if .System }}}}<|im_start|>system
{{{{ .System }}}}<|im_end|>
{{{{ end }}}}{{{{ if .Prompt }}}}<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
{{{{ end }}}}<|im_start|>assistant
{{{{ .Response }}}}<|im_end|>\"\"\"

PARAMETER temperature 0.2
PARAMETER top_p 0.95
PARAMETER num_ctx 8192
PARAMETER stop <|im_start|>
PARAMETER stop <|im_end|>

SYSTEM \"\"\"You are an expert mathematical animation assistant specializing in Manim Community Edition (CE). You write complete, self-contained, fully executable Python scripts inheriting from Scene with rich 2D/3D visualizations.\"\"\"
"""
    modelfile_path = output_dir / "Modelfile"
    modelfile_path.write_text(modelfile_content, encoding="utf-8")
    print(f"✔ Generated Modelfile -> {modelfile_path}")

    # 6. Local Ollama Registration
    if shutil.which("ollama"):
        print(f"\nRegistering with local Ollama: {args.ollama_tag}...")
        try:
            subprocess.run(["ollama", "create", args.ollama_tag, "-f", str(modelfile_path)], check=True)
            subprocess.run(["ollama", "cp", args.ollama_tag, f"hf.co/{args.merged_repo}"], check=True)
            print(f"✔ Successfully registered {args.ollama_tag} and aliased to hf.co/{args.merged_repo}")
        except Exception as e:
            print(f"Notice: local Ollama registration encountered: {e}")

    # 7. Upload to Hugging Face
    if not args.no_push:
        if not token:
            print("Notice: No Hugging Face token found. Skipping upload.")
            return 0

        print("\n[Step 4/4] Deploying to Hugging Face Hub...")
        # A. Upload to dedicated GGUF repo
        print(f"---> Deploying to dedicated GGUF repo: https://huggingface.co/{args.gguf_repo}")
        api.create_repo(args.gguf_repo, repo_type="model", exist_ok=True, token=token)
        api.upload_folder(
            folder_path=str(output_dir),
            repo_id=args.gguf_repo,
            repo_type="model",
            token=token,
            ignore_patterns=["*-f16.gguf"],
        )
        print(f"✔ Deployed to https://huggingface.co/{args.gguf_repo}")

        # B. Upload GGUF binaries + Modelfile into the merged repo as well
        print(f"---> Injecting GGUF models into merged repo: https://huggingface.co/{args.merged_repo}")
        for q in args.quantize_types:
            q_name = f"{args.model_name}-{q}.gguf"
            q_path = output_dir / q_name
            if q_path.is_file():
                api.upload_file(
                    path_or_fileobj=str(q_path),
                    path_in_repo=q_name,
                    repo_id=args.merged_repo,
                    repo_type="model",
                    token=token,
                )
        api.upload_file(
            path_or_fileobj=str(modelfile_path),
            path_in_repo="Modelfile",
            repo_id=args.merged_repo,
            repo_type="model",
            token=token,
        )
        print(f"✔ Injected GGUF artifacts into https://huggingface.co/{args.merged_repo}")

    print("\n=================================================================")
    print("🎉 Qwen2.5-Coder-7B GGUF Deployment Complete!")
    print(f"Run via Ollama: ollama run hf.co/{args.merged_repo}")
    print(f"           or:  ollama run {args.ollama_tag}")
    print("=================================================================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
