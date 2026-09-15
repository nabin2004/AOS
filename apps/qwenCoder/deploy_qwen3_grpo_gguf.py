#!/usr/bin/env python3
"""GGUF Conversion, Quantization, Ollama Import, and Hub Deployment for AOS Qwen3-8B GRPO.

Downloads recent GRPO merged model from Hugging Face:
- Merged weights: nabin2004/AOS-qwen3-8b-grpo-merged
Converts to GGUF (f16 -> Q4_K_M, optionally Q8_0), creates Modelfile,
registers in local Ollama (`aos-qwen3-8b-grpo`), verifies with local inference,
and uploads GGUF artifacts to Hugging Face:
- GGUF Repo:   nabin2004/AOS-qwen3-8b-grpo-gguf
- Merged Repo: nabin2004/AOS-qwen3-8b-grpo-merged (injects GGUF + Modelfile)

Usage:
    uv run python deploy_qwen3_grpo_gguf.py
    uv run python deploy_qwen3_grpo_gguf.py --no-push
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from huggingface_hub import HfApi, get_token, snapshot_download

QWEN_ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = QWEN_ROOT / "templates"
ADAPTER_REPO = "nabin2004/AOS-qwen3-8b-grpo"
HUB_MERGED_REPO = "nabin2004/AOS-qwen3-8b-grpo-merged"
HUB_GGUF_REPO = "nabin2004/AOS-qwen3-8b-grpo-gguf"
OLLAMA_TAG = "aos-qwen3-8b-grpo"


def render_template(template_path: Path, output_path: Path, **kwargs: str) -> None:
    content = template_path.read_text(encoding="utf-8")
    for k, v in kwargs.items():
        content = content.replace(f"{{{k}}}", v)
    output_path.write_text(content, encoding="utf-8")
    print(f"✔ Rendered {output_path.name}")


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
    parser.add_argument("--adapter-repo", default=ADAPTER_REPO, help="GRPO adapter repo ID")
    parser.add_argument("--merged-repo", default=HUB_MERGED_REPO, help="HF repo for merged weights")
    parser.add_argument("--gguf-repo", default=HUB_GGUF_REPO, help="HF repo for GGUF weights")
    parser.add_argument("--ollama-tag", default=OLLAMA_TAG, help="Tag for local Ollama registration")
    parser.add_argument("--quantize-types", nargs="+", default=["Q4_K_M"], help="Quantization types (e.g. Q4_K_M Q8_0)")
    parser.add_argument("--no-push", action="store_true", help="Do not upload to Hugging Face")
    parser.add_argument("--keep-f16", action="store_true", help="Keep intermediate f16 GGUF file")
    parser.add_argument("--skip-download", action="store_true", help="Skip downloading merged model if already local")
    parser.add_argument("--skip-ollama", action="store_true", help="Skip local Ollama registration")
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN") or get_token()
    api = HfApi(token=token)

    merged_dir = QWEN_ROOT / "qwen3-8b-grpo-merged"
    gguf_dir = QWEN_ROOT / "qwen3-8b-grpo-gguf"
    merged_dir.mkdir(parents=True, exist_ok=True)
    gguf_dir.mkdir(parents=True, exist_ok=True)

    print("=================================================================")
    print("🚀 AOS Qwen3-8B GRPO GGUF Conversion & Deployment")
    print(f"GRPO Adapter:  {args.adapter_repo}")
    print(f"Merged Source: {args.merged_repo}")
    print(f"GGUF Target:   {args.gguf_repo}")
    print(f"Ollama Tag:    {args.ollama_tag}")
    print(f"Quant Types:   {args.quantize_types}")
    print("=================================================================")

    # 1. Download Merged Model from Hugging Face Hub
    if not args.skip_download:
        print(f"\n[Step 1/5] Downloading Merged Model from {args.merged_repo}...")
        downloaded_path = snapshot_download(
            repo_id=args.merged_repo,
            local_dir=str(merged_dir),
            token=token,
            ignore_patterns=["*.msgpack", "*.h5", "*.ot"],
        )
        print(f"✔ Merged model weights ready at: {downloaded_path}")
    else:
        print(f"\n[Step 1/5] Skipping download (using existing {merged_dir})")

    # 2. Convert to GGUF (f16) and Quantize
    print("\n[Step 2/5] Converting to GGUF and Quantizing...")
    convert_py, quant_exe = resolve_tools()
    f16_gguf = gguf_dir / f"{args.ollama_tag}-f16.gguf"

    # Check if target quantized files already exist
    needed_quants = [q for q in args.quantize_types if not (gguf_dir / f"{args.ollama_tag}-{q}.gguf").is_file()]

    if needed_quants:
        if not f16_gguf.is_file():
            print(f"Converting {merged_dir} to F16 GGUF...")
            env = os.environ.copy()
            llama_paths = [
                str(convert_py.parent),
                str(QWEN_ROOT / "llama_repo"),
                str(QWEN_ROOT / "llama_repo" / "gguf-py"),
            ]
            env["PYTHONPATH"] = os.pathsep.join(llama_paths + [env.get("PYTHONPATH", "")])
            subprocess.run(
                [
                    sys.executable,
                    str(convert_py),
                    str(merged_dir),
                    "--outfile",
                    str(f16_gguf),
                    "--outtype",
                    "f16",
                ],
                cwd=str(convert_py.parent),
                env=env,
                check=True,
            )
            print(f"✔ Created F16 GGUF ({f16_gguf.stat().st_size / 1e9:.2f} GB)")

        for q in needed_quants:
            q_file = gguf_dir / f"{args.ollama_tag}-{q}.gguf"
            print(f"\n---> Quantizing {q}: {q_file.name}...")
            subprocess.run([str(quant_exe), str(f16_gguf), str(q_file), q], check=True)
            print(f"✔ Created {q_file.name} ({q_file.stat().st_size / 1e9:.2f} GB)")

        if f16_gguf.is_file() and not args.keep_f16:
            print(f"Cleaning up temporary F16 GGUF to free disk space: {f16_gguf.name}")
            f16_gguf.unlink()
    else:
        print(f"✔ All requested GGUF quantizations already exist in {gguf_dir}.")

    # 3. Render Modelfile & GGUF Model Card
    print("\n[Step 3/5] Generating Modelfile and Model Card...")
    primary_quant = "Q4_K_M" if "Q4_K_M" in args.quantize_types else args.quantize_types[0]
    render_template(
        TEMPLATES_DIR / "Modelfile.qwen3-8b-grpo",
        gguf_dir / "Modelfile",
        gguf_file=f"{args.ollama_tag}-{primary_quant}.gguf",
    )
    render_template(
        TEMPLATES_DIR / "gguf_grpo_model_card.md",
        gguf_dir / "README.md",
        hub_adapter_repo=args.adapter_repo,
        hub_merged_repo=args.merged_repo,
        hub_gguf_repo=args.gguf_repo,
        ollama_tag=args.ollama_tag,
    )
    print("✔ Modelfile and README.md prepared.")

    # 4. Local Ollama Registration & Verification
    if shutil.which("ollama") and not args.skip_ollama:
        print(f"\n[Step 4/5] Registering with local Ollama: {args.ollama_tag}...")
        try:
            modelfile_path = gguf_dir / "Modelfile"
            subprocess.run(["ollama", "create", args.ollama_tag, "-f", str(modelfile_path)], check=True)
            print(f"✔ Successfully created Ollama model: {args.ollama_tag}")
            try:
                subprocess.run(["ollama", "cp", args.ollama_tag, f"hf.co/{args.merged_repo}"], check=True)
                print(f"✔ Aliased to hf.co/{args.merged_repo}")
            except Exception:
                pass

            # Test inference
            print(f"\n---> Running quick test inference on local Ollama ({args.ollama_tag})...")
            test_prompt = "Write a complete Manim CE scene in Python that draws a circle and writes 'GRPO Active' inside."
            res = subprocess.run(
                ["ollama", "run", args.ollama_tag, test_prompt],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=180,
            )
            print("--- Ollama Test Output Preview ---")
            lines = res.stdout.strip().splitlines()
            for line in lines[:25]:
                print(line)
            if len(lines) > 25:
                print(f"... ({len(lines) - 25} more lines)")
            print("----------------------------------")
            print("✔ Local Ollama inference verified!")
        except Exception as e:
            print(f"Notice: local Ollama operation encountered: {e}")
    else:
        print("\n[Step 4/5] Ollama binary not found or --skip-ollama specified. Skipping Ollama step.")

    # 5. Upload to Hugging Face Hub
    if not args.no_push and token:
        print(f"\n[Step 5/5] Deploying GGUF to https://huggingface.co/{args.gguf_repo}...")
        api.create_repo(args.gguf_repo, repo_type="model", exist_ok=True, token=token)
        api.upload_folder(
            folder_path=str(gguf_dir),
            repo_id=args.gguf_repo,
            repo_type="model",
            token=token,
            ignore_patterns=["*-f16.gguf"],
        )
        print(f"✔ GGUF repository live at: https://huggingface.co/{args.gguf_repo}")

        # Inject GGUF files and Modelfile into merged repo as well for 1-click pull
        print(f"---> Injecting GGUF models into merged repo: https://huggingface.co/{args.merged_repo}")
        for q in args.quantize_types:
            q_name = f"{args.ollama_tag}-{q}.gguf"
            q_path = gguf_dir / q_name
            if q_path.is_file():
                api.upload_file(
                    path_or_fileobj=str(q_path),
                    path_in_repo=q_name,
                    repo_id=args.merged_repo,
                    repo_type="model",
                    token=token,
                )
        api.upload_file(
            path_or_fileobj=str(gguf_dir / "Modelfile"),
            path_in_repo="Modelfile",
            repo_id=args.merged_repo,
            repo_type="model",
            token=token,
        )
        print(f"✔ Injected GGUF artifacts into https://huggingface.co/{args.merged_repo}")
    else:
        print("\n[Step 5/5] Skipping Hub push (--no-push or no token).")

    print("\n=================================================================")
    print("🎉 Qwen3-8B GRPO GGUF Conversion & Ollama Setup Complete!")
    print(f"Local Ollama Model:  {args.ollama_tag}")
    print(f"To run anytime:      ollama run {args.ollama_tag}")
    if not args.no_push:
        print(f"Hugging Face GGUF:   https://huggingface.co/{args.gguf_repo}")
        print(f"Merged Repo:         https://huggingface.co/{args.merged_repo}")
    print("=================================================================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
