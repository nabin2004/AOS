#!/usr/bin/env python3
"""Streaming Merge, Multi-Quantization, and Deployment for AOS Qwen3-8B Narrated SFT.

Merges Qwen/Qwen3-8B with nabin2004/AOS-qwen3-8b-narrated-adapter layer-by-layer (<500MB RAM),
converts to GGUF (Q4_K_M, Q8_0), generates model cards and Ollama Modelfile, and uploads
both repositories to Hugging Face:
- Merged Safetensors: nabin2004/AOS-qwen3-8b-narrated-sft-merged
- Quantized GGUF:     nabin2004/AOS-qwen3-8b-narrated-sft-gguf

Usage:
    uv run python deploy_qwen3_narrated_sft.py
    uv run python deploy_qwen3_narrated_sft.py --no-push
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

# Guard against broken torchvision binary
try:
    import torchvision  # noqa: F401
except Exception:
    sys.modules["torchvision"] = None

import torch
from huggingface_hub import HfApi, get_token, hf_hub_download
from safetensors import safe_open
from safetensors.torch import load_file, save_file

QWEN_ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = QWEN_ROOT / "templates"
BASE_REPO = "Qwen/Qwen3-8B"
ADAPTER_REPO = "nabin2004/AOS-qwen3-8b-narrated-adapter"
HUB_MERGED_REPO = "nabin2004/AOS-qwen3-8b-narrated-sft-merged"
HUB_GGUF_REPO = "nabin2004/AOS-qwen3-8b-narrated-sft-gguf"
OLLAMA_TAG = "aos-qwen3-8b-narrated-sft"


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
    parser.add_argument("--base-repo", default=BASE_REPO, help="Base foundation model repo")
    parser.add_argument("--adapter-repo", default=ADAPTER_REPO, help="SFT adapter repo ID")
    parser.add_argument("--merged-repo", default=HUB_MERGED_REPO, help="HF repo for merged weights")
    parser.add_argument("--gguf-repo", default=HUB_GGUF_REPO, help="HF repo for GGUF weights")
    parser.add_argument("--ollama-tag", default=OLLAMA_TAG, help="Tag for local Ollama registration")
    parser.add_argument("--quantize-types", nargs="+", default=["Q4_K_M", "Q8_0"], help="Quantization types")
    parser.add_argument("--no-push", action="store_true", help="Do not upload to Hugging Face")
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN") or get_token()
    api = HfApi(token=token)

    merged_dir = QWEN_ROOT / "qwen3-8b-narrated-sft-merged"
    gguf_dir = QWEN_ROOT / "qwen3-8b-narrated-sft-gguf"
    merged_dir.mkdir(parents=True, exist_ok=True)
    gguf_dir.mkdir(parents=True, exist_ok=True)

    print("=================================================================")
    print("🚀 AOS Qwen3-8B Narrated SFT Streaming Merge & Deployment")
    print(f"Base LLM:      {args.base_repo}")
    print(f"SFT Adapter:   {args.adapter_repo}")
    print(f"Merged Target: {args.merged_repo}")
    print(f"GGUF Target:   {args.gguf_repo}")
    print(f"Ollama Tag:    {args.ollama_tag}")
    print("=================================================================")

    # 1. Download Adapter
    print(f"\n[Step 1/6] Loading SFT LoRA Adapter from {args.adapter_repo}...")
    adapter_cfg_file = hf_hub_download(args.adapter_repo, "adapter_config.json", token=token)
    with open(adapter_cfg_file, encoding="utf-8") as f:
        adapter_cfg = json.load(f)

    r = adapter_cfg.get("r", 16)
    alpha = adapter_cfg.get("lora_alpha", 32)
    scaling = float(alpha) / float(r)
    print(f"LoRA parameters: r={r}, alpha={alpha}, scaling={scaling}")

    adapter_weights_file = hf_hub_download(args.adapter_repo, "adapter_model.safetensors", token=token)
    print("Loading adapter tensors...")
    adapter_tensors = load_file(adapter_weights_file)
    print(f"✔ Adapter tensors loaded: {len(adapter_tensors)}")

    # 2. Base Model Metadata & Shard Index
    print(f"\n[Step 2/6] Fetching Base Model Metadata from {args.base_repo}...")
    meta_files = [
        "config.json",
        "generation_config.json",
        "model.safetensors.index.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.json",
    ]
    for mf in meta_files:
        try:
            downloaded = hf_hub_download(args.base_repo, mf, token=token)
            shutil.copy(downloaded, merged_dir / mf)
        except Exception as e:
            print(f"Notice: optional file {mf}: {e}")

    with open(merged_dir / "model.safetensors.index.json", encoding="utf-8") as f:
        index_data = json.load(f)

    weight_map = index_data.get("weight_map", {})
    all_shards = sorted(list(set(weight_map.values())))
    print(f"Base model has {len(all_shards)} shards: {all_shards}")

    # 3. Streaming Layer-by-Layer Merge (<500MB RAM)
    print(f"\n[Step 3/6] Streaming Merge Shard by Shard (<500MB RAM)...")
    for i, shard_name in enumerate(all_shards, 1):
        target_shard = merged_dir / shard_name
        if target_shard.is_file() and target_shard.stat().st_size > 1e9:
            print(f"[{i}/{len(all_shards)}] {shard_name} already exists. Skipping merge.")
            continue

        print(f"\n[{i}/{len(all_shards)}] Resolving base shard: {shard_name}...")
        shard_path = hf_hub_download(args.base_repo, shard_name, token=token)

        print(f"Merging weights for {shard_name}...")
        merged_shard_tensors = {}
        with safe_open(shard_path, framework="pt", device="cpu") as f_in:
            for tensor_name in f_in.keys():
                W = f_in.get_tensor(tensor_name)
                prefix = tensor_name[:-len(".weight")] if tensor_name.endswith(".weight") else tensor_name
                a_key = f"base_model.model.{prefix}.lora_A.weight"
                b_key = f"base_model.model.{prefix}.lora_B.weight"

                if a_key in adapter_tensors and b_key in adapter_tensors:
                    A = adapter_tensors[a_key]
                    B = adapter_tensors[b_key]
                    delta = (torch.matmul(B.float(), A.float()) * scaling).to(W.dtype)
                    merged_shard_tensors[tensor_name] = W + delta
                else:
                    merged_shard_tensors[tensor_name] = W

        print(f"Saving merged shard -> {target_shard} ({len(merged_shard_tensors)} tensors)...")
        save_file(merged_shard_tensors, str(target_shard))
        del merged_shard_tensors
        print(f"✔ Completed shard {i}/{len(all_shards)}")

    # Render Merged Model Card
    render_template(
        TEMPLATES_DIR / "merged_sft_model_card.md",
        merged_dir / "README.md",
        hub_adapter_repo=args.adapter_repo,
        hub_merged_repo=args.merged_repo,
        hub_gguf_repo=args.gguf_repo,
    )
    print("✔ Merged Safetensors weights ready locally.")

    # 4. Upload Merged Safetensors to Hugging Face Hub
    if not args.no_push and token:
        try:
            remote_files = api.list_repo_files(args.merged_repo, token=token)
            already_uploaded = all(s in remote_files for s in all_shards)
        except Exception:
            already_uploaded = False

        if not already_uploaded:
            print(f"\n[Step 4/6] Uploading Merged Model to https://huggingface.co/{args.merged_repo}...")
            api.create_repo(args.merged_repo, repo_type="model", exist_ok=True, token=token)
            api.upload_folder(
                folder_path=str(merged_dir),
                repo_id=args.merged_repo,
                repo_type="model",
                token=token,
            )
            print(f"✔ Merged Safetensors successfully deployed to https://huggingface.co/{args.merged_repo}")
        else:
            print(f"\n[Step 4/6] Merged model already live on Hugging Face: {args.merged_repo}")

    # 5. Convert to GGUF & Multi-Quantize
    print("\n[Step 5/6] Converting to GGUF and Quantizing...")
    convert_py, quant_exe = resolve_tools()
    f16_gguf = gguf_dir / f"{args.ollama_tag}-f16.gguf"

    if not any((gguf_dir / f"{args.ollama_tag}-{q}.gguf").is_file() for q in args.quantize_types):
        if not f16_gguf.is_file():
            print(f"Converting {merged_dir} to F16 GGUF...")
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
                check=True,
            )
            print(f"✔ Created F16 GGUF ({f16_gguf.stat().st_size / 1e9:.2f} GB)")

        for q in args.quantize_types:
            q_file = gguf_dir / f"{args.ollama_tag}-{q}.gguf"
            if not q_file.is_file():
                print(f"\n---> Quantizing {q}: {q_file.name}...")
                subprocess.run([str(quant_exe), str(f16_gguf), str(q_file), q], check=True)
                print(f"✔ Created {q_file.name} ({q_file.stat().st_size / 1e9:.2f} GB)")

        if f16_gguf.is_file():
            print(f"Cleaning up temporary F16 GGUF: {f16_gguf.name}")
            f16_gguf.unlink()
    else:
        print(f"✔ GGUF files already exist in {gguf_dir}. Skipping conversion.")

    # Render Modelfile & GGUF Model Card
    primary_quant = "Q4_K_M" if "Q4_K_M" in args.quantize_types else args.quantize_types[0]
    render_template(
        TEMPLATES_DIR / "Modelfile.qwen3-8b-narrated-sft",
        gguf_dir / "Modelfile",
        gguf_file=f"{args.ollama_tag}-{primary_quant}.gguf",
    )
    render_template(
        TEMPLATES_DIR / "gguf_sft_model_card.md",
        gguf_dir / "README.md",
        hub_adapter_repo=args.adapter_repo,
        hub_merged_repo=args.merged_repo,
        hub_gguf_repo=args.gguf_repo,
        ollama_tag=args.ollama_tag,
    )
    print("✔ GGUF artifacts prepared locally.")

    # 6. Local Ollama Registration
    if shutil.which("ollama"):
        print(f"\nRegistering with local Ollama: {args.ollama_tag}...")
        try:
            subprocess.run(["ollama", "create", args.ollama_tag, "-f", str(gguf_dir / "Modelfile")], check=True)
            subprocess.run(["ollama", "cp", args.ollama_tag, f"hf.co/{args.merged_repo}"], check=True)
            print(f"✔ Successfully registered {args.ollama_tag} and aliased to hf.co/{args.merged_repo}")
        except Exception as e:
            print(f"Notice: local Ollama registration encountered: {e}")

    # 7. Upload GGUF to Hugging Face
    if not args.no_push and token:
        print(f"\n[Step 6/6] Deploying GGUF to https://huggingface.co/{args.gguf_repo}...")
        api.create_repo(args.gguf_repo, repo_type="model", exist_ok=True, token=token)
        api.upload_folder(
            folder_path=str(gguf_dir),
            repo_id=args.gguf_repo,
            repo_type="model",
            token=token,
            ignore_patterns=["*-f16.gguf"],
        )
        print(f"✔ GGUF models deployed to https://huggingface.co/{args.gguf_repo}")

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

    print("\n=================================================================")
    print("🎉 Qwen3-8B Narrated SFT Merging and GGUF Deployment Complete!")
    print(f"Merged Safetensors: https://huggingface.co/{args.merged_repo}")
    print(f"Quantized GGUF:     https://huggingface.co/{args.gguf_repo}")
    print(f"Local Ollama:       ollama run {args.ollama_tag}")
    print(f"                or: ollama run hf.co/{args.merged_repo}")
    print("=================================================================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
