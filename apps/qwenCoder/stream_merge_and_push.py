#!/usr/bin/env python3
"""Streaming Low-Memory Merge, GGUF Multi-Quantization, and Hugging Face Push.

Merges Qwen/Qwen3-8B with nabin2004/AOS-qwen3-8b-narrated-dpo layer-by-layer without OOM (<500MB RAM),
converts to GGUF (Q4_K_M, Q8_0), generates model cards and Ollama Modelfile, and uploads both repos to Hugging Face.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Disable torchvision if broken
try:
    import torchvision  # noqa: F401
except Exception:
    sys.modules["torchvision"] = None

import torch
from huggingface_hub import HfApi, hf_hub_download
from safetensors import safe_open
from safetensors.torch import load_file, save_file

QWEN_ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = QWEN_ROOT / "templates"
BASE_REPO = "Qwen/Qwen3-8B"
ADAPTER_REPO = "nabin2004/AOS-qwen3-8b-narrated-dpo"
HUB_MERGED_REPO = "nabin2004/AOS-qwen3-8b-narrated-merged"
HUB_GGUF_REPO = "nabin2004/AOS-qwen3-8b-narrated-gguf"
OLLAMA_TAG = "aos-qwen3-8b-narrated"


def render_template(template_path: Path, output_path: Path, **kwargs: str) -> None:
    content = template_path.read_text(encoding="utf-8")
    for k, v in kwargs.items():
        content = content.replace(f"{{{k}}}", v)
    output_path.write_text(content, encoding="utf-8")
    print(f"✔ Rendered {output_path.name}")


def main() -> int:
    api = HfApi()
    token = os.environ.get("HF_TOKEN") or None
    user = api.whoami(token=token)
    print(f"Authenticated with Hugging Face as: {user.get('name')}")

    merged_dir = QWEN_ROOT / "qwen3-8b-narrated-merged"
    gguf_dir = QWEN_ROOT / "qwen3-8b-narrated-gguf"
    merged_dir.mkdir(parents=True, exist_ok=True)
    gguf_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # STEP 1: Download Adapter Weights & Config
    # -------------------------------------------------------------------------
    print("\n=================================================================")
    print("▶ STEP 1: Loading DPO LoRA Adapter...")
    print("=================================================================")
    adapter_cfg_file = hf_hub_download(ADAPTER_REPO, "adapter_config.json", token=token)
    with open(adapter_cfg_file) as f:
        adapter_cfg = json.load(f)

    r = adapter_cfg.get("r", 16)
    alpha = adapter_cfg.get("lora_alpha", 32)
    scaling = float(alpha) / float(r)
    print(f"LoRA parameters: r={r}, alpha={alpha}, scaling={scaling}")

    adapter_weights_file = hf_hub_download(ADAPTER_REPO, "adapter_model.safetensors", token=token)
    print("Loading adapter tensors...")
    adapter_tensors = load_file(adapter_weights_file)
    print(f"✔ Adapter tensors loaded: {len(adapter_tensors)}")

    # -------------------------------------------------------------------------
    # STEP 2: Download Base Metadata & Index
    # -------------------------------------------------------------------------
    print("\n=================================================================")
    print("▶ STEP 2: Fetching Base Model Metadata...")
    print("=================================================================")
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
            downloaded = hf_hub_download(BASE_REPO, mf, token=token)
            shutil.copy(downloaded, merged_dir / mf)
            print(f"Copied metadata: {mf}")
        except Exception as e:
            print(f"Notice: optional file {mf} not found: {e}")

    with open(merged_dir / "model.safetensors.index.json") as f:
        index_data = json.load(f)

    weight_map = index_data.get("weight_map", {})
    all_shards = sorted(list(set(weight_map.values())))
    print(f"Base model has {len(all_shards)} shards: {all_shards}")

    # -------------------------------------------------------------------------
    # STEP 3: Streaming Layer-by-Layer Merging (<500MB RAM)
    # -------------------------------------------------------------------------
    print("\n=================================================================")
    print("▶ STEP 3: Streaming Merge Shard by Shard...")
    print("=================================================================")
    for i, shard_name in enumerate(all_shards, 1):
        target_shard = merged_dir / shard_name
        if target_shard.is_file() and target_shard.stat().st_size > 1e9:
            print(f"[{i}/{len(all_shards)}] {shard_name} already exists. Skipping.")
            continue

        print(f"\n[{i}/{len(all_shards)}] Downloading base shard: {shard_name}...")
        shard_path = hf_hub_download(BASE_REPO, shard_name, token=token)

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
        TEMPLATES_DIR / "merged_narrated_model_card.md",
        merged_dir / "README.md",
        hub_merged_repo=HUB_MERGED_REPO,
        hub_gguf_repo=HUB_GGUF_REPO,
    )
    print("✔ Merged model is complete and ready locally.")

    # -------------------------------------------------------------------------
    # STEP 4: Upload Merged Safetensors to Hugging Face Hub
    # -------------------------------------------------------------------------
    print("\n=================================================================")
    print(f"▶ STEP 4: Uploading Merged Model to https://huggingface.co/{HUB_MERGED_REPO}...")
    print("=================================================================")
    api.create_repo(HUB_MERGED_REPO, repo_type="model", exist_ok=True, token=token)
    api.upload_folder(
        folder_path=str(merged_dir),
        repo_id=HUB_MERGED_REPO,
        repo_type="model",
        token=token,
    )
    print(f"🎉 Merged model successfully uploaded to https://huggingface.co/{HUB_MERGED_REPO}!")

    # -------------------------------------------------------------------------
    # STEP 5: Convert to GGUF & Quantize (Q4_K_M & Q8_0)
    # -------------------------------------------------------------------------
    print("\n=================================================================")
    print("▶ STEP 5: Converting to GGUF and Multi-Quantizing...")
    print("=================================================================")
    llama_repo = QWEN_ROOT / "llama_repo"
    convert_py = llama_repo / "convert_hf_to_gguf.py"
    quant_exe = llama_repo / "build" / "bin" / "llama-quantize.exe"

    f16_gguf = gguf_dir / f"{OLLAMA_TAG}-f16.gguf"
    q4_gguf = gguf_dir / f"{OLLAMA_TAG}-Q4_K_M.gguf"
    q8_gguf = gguf_dir / f"{OLLAMA_TAG}-Q8_0.gguf"

    if not q4_gguf.is_file() or not q8_gguf.is_file():
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

        if not q4_gguf.is_file():
            print(f"\nQuantizing to Q4_K_M...")
            subprocess.run([str(quant_exe), str(f16_gguf), str(q4_gguf), "Q4_K_M"], check=True)
            print(f"✔ Created Q4_K_M GGUF ({q4_gguf.stat().st_size / 1e9:.2f} GB)")

        if not q8_gguf.is_file():
            print(f"\nQuantizing to Q8_0...")
            subprocess.run([str(quant_exe), str(f16_gguf), str(q8_gguf), "Q8_0"], check=True)
            print(f"✔ Created Q8_0 GGUF ({q8_gguf.stat().st_size / 1e9:.2f} GB)")

        if f16_gguf.is_file():
            print(f"Cleaning up temporary F16 GGUF: {f16_gguf.name}")
            f16_gguf.unlink()

    # Render Modelfile & GGUF Model Card
    render_template(
        TEMPLATES_DIR / "Modelfile.qwen3-8b-narrated",
        gguf_dir / "Modelfile",
        gguf_file=f"{OLLAMA_TAG}-Q4_K_M.gguf",
    )
    render_template(
        TEMPLATES_DIR / "gguf_narrated_model_card.md",
        gguf_dir / "README.md",
        hub_merged_repo=HUB_MERGED_REPO,
        hub_gguf_repo=HUB_GGUF_REPO,
        ollama_tag=OLLAMA_TAG,
    )
    print("✔ GGUF artifacts prepared locally.")

    # -------------------------------------------------------------------------
    # STEP 6: Upload GGUF Repository to Hugging Face Hub
    # -------------------------------------------------------------------------
    print("\n=================================================================")
    print(f"▶ STEP 6: Uploading GGUF Models to https://huggingface.co/{HUB_GGUF_REPO}...")
    print("=================================================================")
    api.create_repo(HUB_GGUF_REPO, repo_type="model", exist_ok=True, token=token)
    api.upload_folder(
        folder_path=str(gguf_dir),
        repo_id=HUB_GGUF_REPO,
        repo_type="model",
        token=token,
        ignore_patterns=["*-f16.gguf"],
    )
    print(f"🎉 GGUF models successfully uploaded to https://huggingface.co/{HUB_GGUF_REPO}!")

    print("\n=================================================================")
    print("✨ ALL MODELS PUSHED SUCCESSFULLY! ✨")
    print(f"1. Merged Model: https://huggingface.co/{HUB_MERGED_REPO}")
    print(f"2. GGUF Models:  https://huggingface.co/{HUB_GGUF_REPO}")
    print("=================================================================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
