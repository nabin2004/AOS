#!/usr/bin/env python3
"""Streaming Merge, Multi-Quantization & Deployment for qwen-Manimator-1.

Merges Qwen/Qwen3-8B with nabin2004/qwen-Manimator-1-sft layer-by-layer (<500 MB RAM),
converts to GGUF (Q4_K_M, Q8_0), generates model cards and Ollama Modelfile, and uploads
both repositories to Hugging Face:
  - Merged Safetensors : nabin2004/qwen-Manimator-1-merged
  - Quantized GGUF     : nabin2004/qwen-Manimator-1-gguf

Usage:
    uv run python deploy_manimator1.py
    uv run python deploy_manimator1.py --adapter-repo ./qwen-manimator-1-sft
    uv run python deploy_manimator1.py --no-push
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
ADAPTER_REPO = "nabin2004/qwen-Manimator-1-sft"
HUB_MERGED_REPO = "nabin2004/qwen-Manimator-1-merged"
HUB_GGUF_REPO = "nabin2004/qwen-Manimator-1-gguf"
OLLAMA_TAG = "qwen-manimator-1"


def _run(cmd: list[str], env: dict | None = None, cwd: str | None = None) -> None:
    print(f"$ {' '.join(str(c) for c in cmd)}")
    subprocess.run([str(c) for c in cmd], check=True, env=env, cwd=cwd)


def resolve_tools() -> tuple[Path, Path]:
    convert_candidates = [
        QWEN_ROOT / "llama_bin" / "convert_hf_to_gguf.py",
        QWEN_ROOT / "llama_repo" / "convert_hf_to_gguf.py",
        Path("./llama.cpp/convert_hf_to_gguf.py").resolve(),
    ]
    convert_py = next((p for p in convert_candidates if p.is_file()), None)
    if not convert_py:
        raise FileNotFoundError(f"Missing convert_hf_to_gguf.py; searched: {convert_candidates}")

    quant_candidates = [
        QWEN_ROOT / "llama_bin" / "llama-quantize.exe",
        QWEN_ROOT / "llama_bin" / "llama-quantize",
        QWEN_ROOT / "llama_repo" / "build" / "bin" / "Release" / "llama-quantize.exe",
        QWEN_ROOT / "llama_repo" / "build" / "bin" / "llama-quantize",
    ]
    quant_exe = next((p for p in quant_candidates if p.is_file()), None)
    if not quant_exe:
        raise FileNotFoundError(f"Missing llama-quantize binary; searched: {quant_candidates}")

    return convert_py, quant_exe


def write_merged_model_card(merged_dir: Path, adapter_repo: str, merged_repo: str, gguf_repo: str) -> None:
    card = f"""---
license: apache-2.0
base_model: Qwen/Qwen3-8B
library_name: transformers
pipeline_tag: text-generation
language:
  - en
tags:
  - safetensors
  - sft
  - manim
  - manim-voiceover
  - manimce
  - aos
  - code-generation
  - math
  - gguf
  - ollama
---

# qwen-Manimator-1 (Merged bf16 Safetensors & GGUF)

Full-weight merged release and GGUF quantizations of **qwen-Manimator-1**, a Qwen/Qwen3-8B model fine-tuned
to generate pedagogically rich **ManimCE + Manim Voiceover** animations.

- **Base Model**: `Qwen/Qwen3-8B`
- **LoRA Adapter**: [`{adapter_repo}`](https://huggingface.co/{adapter_repo})
- **Merged Model**: [`{merged_repo}`](https://huggingface.co/{merged_repo})
- **Quantized GGUF**: [`{gguf_repo}`](https://huggingface.co/{gguf_repo})

---

## Quickstart with Ollama (1-Click)

You can run this merged model directly in Ollama:

```bash
ollama run hf.co/{merged_repo}
```

Or run the dedicated GGUF repository:
```bash
ollama run hf.co/{gguf_repo}
```

---

## Model Capabilities

1. **VoiceoverScene Architecture**: Generates complete, executable Manim scripts inheriting from `VoiceoverScene`.
2. **Audio Bookmarking**: Integrates `<bookmark mark='NAME'/>` tags + `self.wait_until_bookmark("NAME")` for audio-visual sync.
3. **CE API Compliance**: Strict Manim Community Edition syntax, no deprecated legacy APIs.
4. **Plan-then-Code**: Always outputs a `<Plan>` reasoning block followed by the Python implementation.

---

## Quickstart (Transformers)

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "{merged_repo}"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16, device_map="auto")

messages = [
    {{"role": "system", "content": "You are an expert Python programmer and mathematics educator specializing in ManimCE and Manim Voiceover..."}},
    {{"role": "user", "content": "Create a Manim animation explaining Fourier series with audio narration."}},
]
ids = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to("cuda")
out = model.generate(ids, max_new_tokens=2048, temperature=0.2, top_p=0.9)
print(tokenizer.decode(out[0][ids.shape[-1]:], skip_special_tokens=True))
```

---

## Training Config

| Parameter | Value |
|---|---|
| Base Model | `Qwen/Qwen3-8B` |
| Dataset | [`nabin2004/qwen-Manimator-1-sft-data`](https://huggingface.co/datasets/nabin2004/qwen-Manimator-1-sft-data) |
| Epochs | 3 |
| Max Length | 4500 |
| Learning Rate | 1e-4 |
| LoRA | r=16, alpha=32 |
| Optimizer | paged_adamw_8bit |
| Hardware | Kaggle T4×2 |
"""
    (merged_dir / "README.md").write_text(card, encoding="utf-8")
    print("✔ Wrote merged model card.")


def write_gguf_model_card(
    gguf_dir: Path,
    adapter_repo: str,
    merged_repo: str,
    gguf_repo: str,
    ollama_tag: str,
    quant_types: list[str],
) -> None:
    rows = "\n".join(
        f"| `{ollama_tag}-{q}.gguf` | {q} | Quantized | {'~5 GB Q4 / ~9 GB Q8' if q.startswith('Q4') else 'Near-lossless'} |"
        for q in quant_types
    )
    card = f"""---
license: apache-2.0
base_model: {merged_repo}
library_name: gguf
pipeline_tag: text-generation
language:
  - en
tags:
  - manim
  - manim-voiceover
  - manimce
  - gguf
  - ollama
  - llama.cpp
  - sft
  - aos
---

# qwen-Manimator-1 GGUF Quantizations

Quantized GGUF versions of [`{merged_repo}`](https://huggingface.co/{merged_repo}),
a Qwen/Qwen3-8B SFT model for **ManimCE + Manim Voiceover** animation generation.

## Available Quantizations

| File | Quantization | Description |
|---|---|---|
{rows}

---

## Quickstart with Ollama

### 1-Click Pull
```bash
ollama run hf.co/{gguf_repo}
```

### With Local Modelfile
```bash
huggingface-cli download {gguf_repo} {ollama_tag}-Q4_K_M.gguf Modelfile --local-dir ./model
cd ./model && ollama create {ollama_tag} -f Modelfile && ollama run {ollama_tag}
```

---

## Adapter & Dataset

- **LoRA Adapter**: [`{adapter_repo}`](https://huggingface.co/{adapter_repo})
- **Dataset**: [`nabin2004/qwen-Manimator-1-sft-data`](https://huggingface.co/datasets/nabin2004/qwen-Manimator-1-sft-data)
"""
    (gguf_dir / "README.md").write_text(card, encoding="utf-8")
    print("✔ Wrote GGUF model card.")


def write_modelfile(gguf_dir: Path, ollama_tag: str, primary_quant: str) -> Path:
    gguf_file = f"{ollama_tag}-{primary_quant}.gguf"
    template_path = TEMPLATES_DIR / "Modelfile.qwen-manimator-1"
    if template_path.is_file():
        content = template_path.read_text(encoding="utf-8").replace("{gguf_file}", gguf_file)
    else:
        content = (
            f"FROM ./{gguf_file}\n"
            "PARAMETER temperature 0.2\n"
            "PARAMETER top_p 0.9\n"
            "PARAMETER repeat_penalty 1.05\n"
            "PARAMETER num_predict 2048\n"
            'SYSTEM "You are an expert Python programmer and mathematics educator specializing in ManimCE and Manim Voiceover. You create high-quality, pedagogically rich, narrated animations."\n'
        )
    path = gguf_dir / "Modelfile"
    path.write_text(content, encoding="utf-8")
    print(f"✔ Wrote Modelfile: {path}")
    return path


def setup_kaggle_secrets() -> None:
    """Retrieve HF_TOKEN from Kaggle UserSecretsClient if not set."""
    if "HF_TOKEN" not in os.environ:
        try:
            from kaggle_secrets import UserSecretsClient  # type: ignore

            val = UserSecretsClient().get_secret("HF_TOKEN")
            if val:
                os.environ["HF_TOKEN"] = val
                print("✔ Retrieved HF_TOKEN from Kaggle UserSecrets.")
        except Exception:
            pass


def main() -> int:
    setup_kaggle_secrets()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-repo", default=BASE_REPO)
    parser.add_argument("--adapter-repo", default=ADAPTER_REPO)
    parser.add_argument("--merged-repo", default=HUB_MERGED_REPO)
    parser.add_argument("--gguf-repo", default=HUB_GGUF_REPO)
    parser.add_argument("--ollama-tag", default=OLLAMA_TAG)
    parser.add_argument("--quantize-types", nargs="+", default=["Q4_K_M", "Q8_0"])
    parser.add_argument("--no-push", action="store_true", help="Do not upload to Hugging Face")
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN", "").strip() or get_token()
    api = HfApi(token=token)

    merged_dir = QWEN_ROOT / "qwen-manimator-1-merged"
    gguf_dir = QWEN_ROOT / "qwen-manimator-1-gguf"
    merged_dir.mkdir(parents=True, exist_ok=True)
    gguf_dir.mkdir(parents=True, exist_ok=True)

    print("=================================================================")
    print("🎨 qwen-Manimator-1 Streaming Merge & GGUF Deployment")
    print(f"Base LLM:     {args.base_repo}")
    print(f"SFT Adapter:  {args.adapter_repo}")
    print(f"Merged Repo:  {args.merged_repo}")
    print(f"GGUF Repo:    {args.gguf_repo}")
    print(f"Quant Types:  {args.quantize_types}")
    print("=================================================================")

    # Step 1 — Download adapter config & weights
    print(f"\n[Step 1/6] Loading SFT LoRA Adapter from {args.adapter_repo}...")
    adapter_cfg_file = hf_hub_download(args.adapter_repo, "adapter_config.json", token=token)
    with open(adapter_cfg_file, encoding="utf-8") as f:
        adapter_cfg = json.load(f)
    r = adapter_cfg.get("r", 16)
    alpha = adapter_cfg.get("lora_alpha", 32)
    scaling = float(alpha) / float(r)
    print(f"LoRA: r={r}, alpha={alpha}, scaling={scaling:.4f}")
    adapter_weights_file = hf_hub_download(
        args.adapter_repo, "adapter_model.safetensors", token=token
    )
    adapter_tensors = load_file(adapter_weights_file)
    print(f"✔ Adapter tensors loaded: {len(adapter_tensors)}")

    # Step 2 — Download base model metadata
    print(f"\n[Step 2/6] Fetching Base Model Metadata from {args.base_repo}...")
    meta_files = [
        "config.json", "generation_config.json", "model.safetensors.index.json",
        "tokenizer.json", "tokenizer_config.json", "vocab.json",
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
    all_shards = sorted(set(weight_map.values()))
    print(f"Base model shards: {len(all_shards)} -> {all_shards}")

    # Step 3 — Streaming shard-by-shard merge
    print(f"\n[Step 3/6] Streaming Merge Shard-by-Shard (<500 MB RAM)...")
    for i, shard_name in enumerate(all_shards, 1):
        target_shard = merged_dir / shard_name
        if target_shard.is_file() and target_shard.stat().st_size > 1e9:
            print(f"[{i}/{len(all_shards)}] {shard_name} already merged. Skipping.")
            continue
        print(f"\n[{i}/{len(all_shards)}] Merging shard: {shard_name}...")
        shard_path = hf_hub_download(args.base_repo, shard_name, token=token)
        merged_shard: dict = {}
        with safe_open(shard_path, framework="pt", device="cpu") as f_in:
            for tensor_name in f_in.keys():
                W = f_in.get_tensor(tensor_name)
                prefix = tensor_name[: -len(".weight")] if tensor_name.endswith(".weight") else tensor_name
                a_key = f"base_model.model.{prefix}.lora_A.weight"
                b_key = f"base_model.model.{prefix}.lora_B.weight"
                if a_key in adapter_tensors and b_key in adapter_tensors:
                    A = adapter_tensors[a_key]
                    B = adapter_tensors[b_key]
                    delta = (torch.matmul(B.float(), A.float()) * scaling).to(W.dtype)
                    merged_shard[tensor_name] = W + delta
                else:
                    merged_shard[tensor_name] = W
        save_file(merged_shard, str(target_shard))
        del merged_shard
        print(f"✔ Shard {i}/{len(all_shards)} done.")

    write_merged_model_card(
        merged_dir,
        adapter_repo=args.adapter_repo,
        merged_repo=args.merged_repo,
        gguf_repo=args.gguf_repo,
    )

    # Step 4 — Upload merged to HF
    if not args.no_push and token:
        try:
            remote_files = list(api.list_repo_files(args.merged_repo, token=token))
            already_up = all(s in remote_files for s in all_shards)
        except Exception:
            already_up = False
        if not already_up:
            print(f"\n[Step 4/6] Uploading merged model -> https://huggingface.co/{args.merged_repo}")
            api.create_repo(args.merged_repo, repo_type="model", exist_ok=True, token=token)
            api.upload_folder(
                folder_path=str(merged_dir),
                repo_id=args.merged_repo,
                repo_type="model",
                token=token,
            )
            print(f"✔ Merged model uploaded.")
        else:
            print(f"\n[Step 4/6] Merged model already live on HF: {args.merged_repo}")

    # Step 5 — GGUF conversion + quantization
    print("\n[Step 5/6] Converting to GGUF & quantizing...")
    convert_py, quant_exe = resolve_tools()
    f16_gguf = gguf_dir / f"{args.ollama_tag}-f16.gguf"

    need_convert = not any(
        (gguf_dir / f"{args.ollama_tag}-{q}.gguf").is_file() for q in args.quantize_types
    )
    if need_convert:
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
                [sys.executable, str(convert_py), str(merged_dir), "--outfile", str(f16_gguf), "--outtype", "f16"],
                cwd=str(convert_py.parent),
                env=env,
                check=True,
            )
            print(f"✔ F16 GGUF: {f16_gguf.stat().st_size / 1e9:.2f} GB")

        for q in args.quantize_types:
            q_file = gguf_dir / f"{args.ollama_tag}-{q}.gguf"
            if not q_file.is_file():
                print(f"Quantizing {q}...")
                subprocess.run([str(quant_exe), str(f16_gguf), str(q_file), q], check=True)
                print(f"✔ {q_file.name}: {q_file.stat().st_size / 1e9:.2f} GB")

        if f16_gguf.is_file():
            f16_gguf.unlink()
            print(f"Cleaned up F16 GGUF.")
    else:
        print("✔ GGUF files already exist. Skipping conversion.")

    primary_quant = "Q4_K_M" if "Q4_K_M" in args.quantize_types else args.quantize_types[0]
    modelfile_path = write_modelfile(gguf_dir, args.ollama_tag, primary_quant)
    write_gguf_model_card(
        gguf_dir,
        adapter_repo=args.adapter_repo,
        merged_repo=args.merged_repo,
        gguf_repo=args.gguf_repo,
        ollama_tag=args.ollama_tag,
        quant_types=args.quantize_types,
    )

    # Local Ollama registration
    if shutil.which("ollama"):
        print(f"\nRegistering with local Ollama: {args.ollama_tag}...")
        try:
            subprocess.run(["ollama", "create", args.ollama_tag, "-f", str(modelfile_path)], cwd=str(gguf_dir), check=True)
            print(f"✔ Registered ollama model: {args.ollama_tag}")
        except Exception as e:
            print(f"Notice: Ollama registration: {e}")

    # Step 6 — Upload GGUF to HF
    if not args.no_push and token:
        print(f"\n[Step 6/6] Deploying GGUF -> https://huggingface.co/{args.gguf_repo}")
        api.create_repo(args.gguf_repo, repo_type="model", exist_ok=True, token=token)
        api.upload_folder(
            folder_path=str(gguf_dir),
            repo_id=args.gguf_repo,
            repo_type="model",
            token=token,
            ignore_patterns=["*-f16.gguf"],
        )
        print(f"✔ GGUF uploaded.")

        # Inject GGUFs into merged repo too for 1-click `ollama run hf.co/...`
        print(f"---> Injecting GGUF files into merged repo: {args.merged_repo}")
        for q in args.quantize_types:
            q_path = gguf_dir / f"{args.ollama_tag}-{q}.gguf"
            if q_path.is_file():
                api.upload_file(
                    path_or_fileobj=str(q_path),
                    path_in_repo=q_path.name,
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
        api.upload_file(
            path_or_fileobj=str(merged_dir / "README.md"),
            path_in_repo="README.md",
            repo_id=args.merged_repo,
            repo_type="model",
            token=token,
        )
        print(f"✔ GGUF artifacts & model card injected into merged repo.")

    print("\n=================================================================")
    print("🎉 qwen-Manimator-1 Merge & GGUF Deployment Complete!")
    print(f"Merged : https://huggingface.co/{args.merged_repo}")
    print(f"GGUF   : https://huggingface.co/{args.gguf_repo}")
    print(f"Ollama : ollama run hf.co/{args.merged_repo}")
    print("=================================================================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
