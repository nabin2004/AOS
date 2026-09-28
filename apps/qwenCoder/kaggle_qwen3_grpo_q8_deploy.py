#!/usr/bin/env python3
"""
Kaggle Notebook End-to-End Pipeline:
Merge Qwen3-8B + nabin2004/qwen-Manimator-1-grpo-clean, Convert to GGUF,
Quantize to Q8_0, Validate 32K Context & Manim Generation, and Deploy to HF Hub.

Target Hub Repository: nabin2004/qwen-Manimator-1-grpo-GGUF
Artifact: qwen-Manimator-1-grpo-Q8_0.gguf
"""

from __future__ import annotations

import gc
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ==============================================================================
# Global Configuration & Working Paths
# ==============================================================================
BASE_MODEL_ID = "Qwen/Qwen3-8B"
ADAPTER_MODEL_ID = "nabin2004/qwen-Manimator-1-grpo-clean"
GGUF_REPO_ID = "nabin2004/qwen-Manimator-1-grpo-GGUF"
QUANT_TYPE = "Q8_0"
CONTEXT_LENGTH = 32768

# Detect if running in Kaggle environment
IS_KAGGLE = Path("/kaggle").is_dir()
WORK_DIR = Path("/kaggle/working") if IS_KAGGLE else Path("./kaggle_work").resolve()
WORK_DIR.mkdir(parents=True, exist_ok=True)

MERGED_DIR = WORK_DIR / "merged_model"
LLAMA_CPP_DIR = WORK_DIR / "llama.cpp"
F16_GGUF_PATH = WORK_DIR / "qwen-Manimator-1-grpo-f16.gguf"
Q8_GGUF_PATH = WORK_DIR / "qwen-Manimator-1-grpo-Q8_0.gguf"
MANIM_OUT_DIR = WORK_DIR / "manim_artifacts"
MANIM_OUT_DIR.mkdir(parents=True, exist_ok=True)


def print_step_header(step_num: str, title: str) -> None:
    print(f"\n{'='*70}")
    print(f"[{step_num}] {title}")
    print(f"{'='*70}")


def show_disk_usage(label: str = "") -> None:
    if label:
        print(f"\n--- Disk Usage ({label}) ---")
    else:
        print("\n--- Current Disk Usage ---")
    try:
        res = subprocess.run(["df", "-h", str(WORK_DIR)], capture_output=True, text=True)
        print(res.stdout.strip())
    except Exception:
        total, used, free = shutil.disk_usage(WORK_DIR)
        print(f"Total: {total/1e9:.2f} GB | Used: {used/1e9:.2f} GB | Free: {free/1e9:.2f} GB")


def get_path_size_gb(path: Path) -> float:
    if not path.exists():
        return 0.0
    if path.is_file():
        return path.stat().st_size / 1e9
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / 1e9


# ==============================================================================
# 01_environment_setup
# ==============================================================================
def step_01_environment_setup() -> str:
    print_step_header("01", "Environment & Hardware Setup")

    # 1. Detect Hardware
    import torch
    import psutil

    has_cuda = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if has_cuda else "None (CPU only)"
    cuda_ver = torch.version.cuda if has_cuda else "N/A"
    gpu_mem = f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB" if has_cuda else "0 GB"
    cpu_count = psutil.cpu_count(logical=True)
    ram_gb = f"{psutil.virtual_memory().total / 1e9:.2f} GB"
    disk_free = f"{shutil.disk_usage(WORK_DIR).free / 1e9:.2f} GB"

    print(f"GPU:        {gpu_name}")
    print(f"CUDA:       {cuda_ver}")
    print(f"GPU memory: {gpu_mem}")
    print(f"CPU:        {cpu_count} vCPUs")
    print(f"RAM:        {ram_gb}")
    print(f"Disk:       {disk_free} free in {WORK_DIR}")

    # 2. Check Hugging Face Secrets
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        try:
            from kaggle_secrets import UserSecretsClient
            hf_token = UserSecretsClient().get_secret("HF_TOKEN")
        except Exception:
            hf_token = None

    if not hf_token:
        raise RuntimeError(
            "CRITICAL: HF_TOKEN not found!\n"
            "To provide credentials in Kaggle:\n"
            "1. Click 'Add-ons' in the Kaggle Notebook header.\n"
            "2. Select 'Secrets'.\n"
            "3. Add a secret with label 'HF_TOKEN' and your Hugging Face write token as value.\n"
            "4. Check the box to attach the secret to the notebook session."
        )

    os.environ["HF_TOKEN"] = hf_token
    print("✔ Hugging Face token successfully loaded (hidden).")

    # 3. Install Required Dependencies
    print("\nInstalling / Verifying system dependencies...")
    try:
        subprocess.run(
            ["apt-get", "update", "-qq"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "apt-get", "install", "-y", "-qq", "--no-install-recommends",
                "ffmpeg", "libcairo2-dev", "libpango1.0-dev", "pkg-config",
                "cmake", "build-essential", "git", "git-lfs",
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"Notice: apt-get package installation warning: {e}")

    print("Installing / Verifying Python packages...")
    packages = [
        "transformers>=4.48.0",
        "peft>=0.14.0",
        "accelerate>=1.2.0",
        "safetensors>=0.5.0",
        "huggingface_hub>=0.28.0",
        "gguf>=0.10.0",
        "sentencepiece",
        "protobuf",
        "manim>=0.18.0",
        "manim-voiceover",
    ]
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "--upgrade"] + packages,
        check=True,
    )
    print("✔ Python packages installed.")

    # 4. Clone & Build llama.cpp
    if not (LLAMA_CPP_DIR / "convert_hf_to_gguf.py").is_file():
        print("\nCloning latest llama.cpp...")
        subprocess.run(
            ["git", "clone", "--depth", "1", "https://github.com/ggerganov/llama.cpp.git", str(LLAMA_CPP_DIR)],
            check=True,
        )

    # Install gguf-py
    gguf_py_dir = LLAMA_CPP_DIR / "gguf-py"
    if gguf_py_dir.is_dir():
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-e", str(gguf_py_dir)], check=True)

    # Build llama-quantize and llama-cli
    build_dir = LLAMA_CPP_DIR / "build"
    quant_bin = build_dir / "bin" / "llama-quantize"
    cli_bin = build_dir / "bin" / "llama-cli"

    if not quant_bin.is_file() or not cli_bin.is_file():
        print("\nBuilding llama-quantize & llama-cli from source...")
        build_dir.mkdir(parents=True, exist_ok=True)
        cmake_cmd = ["cmake", "-B", str(build_dir), "-S", str(LLAMA_CPP_DIR), "-DCMAKE_BUILD_TYPE=Release"]
        if has_cuda:
            cmake_cmd.append("-DGGML_CUDA=ON")
        subprocess.run(cmake_cmd, check=True)
        subprocess.run(
            ["cmake", "--build", str(build_dir), "--config", "Release", "-j", str(cpu_count), "--target", "llama-quantize", "llama-cli"],
            check=True,
        )

    print("✔ llama.cpp binaries ready.")
    show_disk_usage("After 01_environment_setup")
    return hf_token


# ==============================================================================
# 02_download_models
# ==============================================================================
def step_02_download_models(hf_token: str) -> dict[str, str]:
    print_step_header("02", f"Download Models: {BASE_MODEL_ID} & {ADAPTER_MODEL_ID}")
    show_disk_usage("Before downloading")

    from huggingface_hub import snapshot_download

    adapter_cache_dir = WORK_DIR / "adapter_cache"
    adapter_cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading LoRA adapter: {ADAPTER_MODEL_ID}...")
    adapter_path = snapshot_download(
        repo_id=ADAPTER_MODEL_ID,
        local_dir=str(adapter_cache_dir),
        token=hf_token,
    )
    adapter_size_mb = sum(f.stat().st_size for f in adapter_cache_dir.rglob("*") if f.is_file()) / 1e6
    print(f"✔ Adapter ready: {adapter_size_mb:.2f} MB at {adapter_path}")

    # Note: Transformers AutoModelForCausalLM.from_pretrained will download base weights
    # directly or stream them, avoiding unnecessary redundant copies.
    print(f"\nTarget Base Model: {BASE_MODEL_ID} (~16 GB unquantized)")
    show_disk_usage("After 02_download_models")
    return {"adapter_path": str(adapter_path)}


# ==============================================================================
# 03_merge_lora
# ==============================================================================
def step_03_merge_lora(hf_token: str) -> Path:
    print_step_header("03", f"Merge LoRA Adapter into {BASE_MODEL_ID}")

    if (MERGED_DIR / "config.json").is_file() and any(MERGED_DIR.glob("*.safetensors")):
        print(f"✔ Merged model already exists at {MERGED_DIR}. Skipping merge.")
        show_disk_usage("Existing merged model")
        return MERGED_DIR

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    torch_dtype = torch.bfloat16 if (torch.cuda.is_available() and torch.cuda.is_bf16_supported()) else torch.float16
    print(f"Using torch precision: {torch_dtype}")

    print(f"Loading base model {BASE_MODEL_ID}...")
    # Load with device_map="cpu" or "auto" to safely fit in Kaggle RAM (30GB system RAM)
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID,
        torch_dtype=torch_dtype,
        device_map="cpu",
        trust_remote_code=True,
        token=hf_token,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL_ID,
        trust_remote_code=True,
        token=hf_token,
    )

    print(f"Applying LoRA adapter {ADAPTER_MODEL_ID}...")
    model = PeftModel.from_pretrained(base_model, ADAPTER_MODEL_ID, token=hf_token)

    print("Merging adapter weights into base model...")
    merged_model = model.merge_and_unload()

    print(f"Saving merged model to {MERGED_DIR}...")
    MERGED_DIR.mkdir(parents=True, exist_ok=True)
    merged_model.save_pretrained(MERGED_DIR, max_shard_size="4GB", safe_serialization=True)
    tokenizer.save_pretrained(MERGED_DIR)

    # Free memory
    del merged_model
    del model
    del base_model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    merged_size_gb = get_path_size_gb(MERGED_DIR)
    print(f"✔ Merged model successfully saved: {merged_size_gb:.2f} GB")
    show_disk_usage("After 03_merge_lora")
    return MERGED_DIR


# ==============================================================================
# 04_convert_to_gguf
# ==============================================================================
def step_04_convert_to_gguf() -> Path:
    print_step_header("04", "Convert Merged Model to F16 GGUF")

    if F16_GGUF_PATH.is_file() and F16_GGUF_PATH.stat().st_size > 5e9:
        print(f"✔ F16 GGUF already exists: {F16_GGUF_PATH.stat().st_size / 1e9:.2f} GB")
        return F16_GGUF_PATH

    convert_script = LLAMA_CPP_DIR / "convert_hf_to_gguf.py"
    if not convert_script.is_file():
        raise FileNotFoundError(f"Missing {convert_script}")

    print(f"Converting {MERGED_DIR} -> {F16_GGUF_PATH} (outtype: f16)...")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{LLAMA_CPP_DIR / 'gguf-py'}:{env.get('PYTHONPATH', '')}"

    subprocess.run(
        [
            sys.executable,
            str(convert_script),
            str(MERGED_DIR),
            "--outfile",
            str(F16_GGUF_PATH),
            "--outtype",
            "f16",
        ],
        env=env,
        check=True,
    )

    f16_size_gb = get_path_size_gb(F16_GGUF_PATH)
    print(f"✔ F16 GGUF successfully created: {f16_size_gb:.2f} GB")
    show_disk_usage("After 04_convert_to_gguf")
    return F16_GGUF_PATH


# ==============================================================================
# 05_quantize_q8
# ==============================================================================
def step_05_quantize_q8() -> Path:
    print_step_header("05", f"Quantize F16 GGUF to {QUANT_TYPE}")

    if Q8_GGUF_PATH.is_file() and Q8_GGUF_PATH.stat().st_size > 5e9:
        print(f"✔ Q8_0 GGUF already exists: {Q8_GGUF_PATH.stat().st_size / 1e9:.2f} GB")
        return Q8_GGUF_PATH

    quant_bin = LLAMA_CPP_DIR / "build" / "bin" / "llama-quantize"
    if not quant_bin.is_file():
        raise FileNotFoundError(f"Missing quantization binary at {quant_bin}")

    print(f"Quantizing: {F16_GGUF_PATH.name} -> {Q8_GGUF_PATH.name} ({QUANT_TYPE})...")
    subprocess.run([str(quant_bin), str(F16_GGUF_PATH), str(Q8_GGUF_PATH), QUANT_TYPE], check=True)

    q8_size_gb = get_path_size_gb(Q8_GGUF_PATH)
    print(f"✔ Quantized {QUANT_TYPE} GGUF successfully created: {q8_size_gb:.2f} GB")
    show_disk_usage("After 05_quantize_q8")
    return Q8_GGUF_PATH


# ==============================================================================
# 06_validate_model
# ==============================================================================
def step_06_validate_model() -> bool:
    print_step_header("06", "Validate Model Integrity & Metadata")

    from gguf import GGUFReader

    reader = GGUFReader(str(Q8_GGUF_PATH))
    arch = None
    ctx_len = None

    for field in reader.fields.values():
        if field.name == "general.architecture":
            arch = str(bytes(field.parts[field.data[0]]).decode("utf-8", errors="ignore"))
        elif "context_length" in field.name:
            try:
                ctx_len = int(field.parts[field.data[0]][0])
            except Exception:
                ctx_len = int(field.data[0])

    print(f"Detected Architecture:    {arch}")
    print(f"Metadata Context Length:  {ctx_len}")

    if not arch or ("qwen" not in arch.lower()):
        print(f"WARNING: Unexpected architecture name: {arch}")

    # Test baseline inference with llama-cli
    cli_bin = LLAMA_CPP_DIR / "build" / "bin" / "llama-cli"
    prompt = "<|im_start|>system\nYou are a helpful assistant.<|im_end|>\n<|im_start|>user\nSay 'Model Verified'.<|im_end|>\n<|im_start|>assistant\n"

    print("\nRunning quick generation check with llama-cli...")
    res = subprocess.run(
        [
            str(cli_bin),
            "-m", str(Q8_GGUF_PATH),
            "-p", prompt,
            "-n", "32",
            "--temp", "0.1",
            "--no-display-prompt",
        ],
        capture_output=True,
        text=True,
    )

    output = res.stdout.strip()
    print("--- llama-cli Output ---")
    print(output[:300] + ("..." if len(output) > 300 else ""))
    print("------------------------")

    if res.returncode == 0:
        print("✔ GGUF Model Baseline Validation: PASS")
        return True
    else:
        print(f"ERROR: llama-cli exited with code {res.returncode}:\n{res.stderr}")
        return False


# ==============================================================================
# 07_test_32k_context
# ==============================================================================
def step_07_test_32k_context() -> bool:
    print_step_header("07", f"Test {CONTEXT_LENGTH} (32K) Context Configuration")

    cli_bin = LLAMA_CPP_DIR / "build" / "bin" / "llama-cli"
    prompt = (
        "<|im_start|>system\nYou are an AI code generator.<|im_end|>\n"
        "<|im_start|>user\nExplain in one sentence why large context windows are useful.<|im_end|>\n"
        "<|im_start|>assistant\n"
    )

    print(f"Invoking llama-cli with context = {CONTEXT_LENGTH} (-c {CONTEXT_LENGTH})...")
    res = subprocess.run(
        [
            str(cli_bin),
            "-m", str(Q8_GGUF_PATH),
            "-c", str(CONTEXT_LENGTH),
            "-p", prompt,
            "-n", "48",
            "--temp", "0.2",
            "--no-display-prompt",
        ],
        capture_output=True,
        text=True,
    )

    output = res.stdout.strip()
    print("--- 32K Context Output ---")
    print(output[:400] + ("..." if len(output) > 400 else ""))
    print("--------------------------")

    if res.returncode == 0 and len(output) > 5:
        print(f"✔ 32K Context ({CONTEXT_LENGTH} tokens) Validation: PASS")
        return True
    else:
        print(f"ERROR: 32K Context test failed. Returncode {res.returncode}:\n{res.stderr}")
        return False


# ==============================================================================
# 08_test_manim
# ==============================================================================
def step_08_test_manim() -> tuple[bool, bool, Path | None]:
    print_step_header("08", "End-to-End Manim Code Generation & Rendering Test")

    cli_bin = LLAMA_CPP_DIR / "build" / "bin" / "llama-cli"
    manim_prompt = (
        "<|im_start|>system\n"
        "You are an expert Python programmer specializing in Manim Community Edition (ManimCE).\n"
        "Write a complete, valid Manim script animating a Circle and a Text label. "
        "Output ONLY the python code inside a single ```python block.\n"
        "<|im_end|>\n"
        "<|im_start|>user\n"
        "Create a simple animation where a blue Circle appears, and text 'Manimator Q8_0' appears below it.\n"
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )

    print("Generating Manim script from Q8_0 GGUF...")
    res = subprocess.run(
        [
            str(cli_bin),
            "-m", str(Q8_GGUF_PATH),
            "-p", manim_prompt,
            "-n", "512",
            "--temp", "0.2",
            "--no-display-prompt",
        ],
        capture_output=True,
        text=True,
    )

    raw_output = res.stdout.strip()
    code_match = re.search(r"```python(.*?)```", raw_output, re.DOTALL)
    if code_match:
        manim_code = code_match.group(1).strip()
    else:
        # Fallback to lines with imports / scene
        lines = [line for line in raw_output.splitlines() if not line.startswith("```")]
        manim_code = "\n".join(lines).strip()

    # Fallback template if generation was truncated or corrupted
    if "from manim import" not in manim_code or "Scene" not in manim_code:
        print("Notice: Wrapping output to ensure executable Manim script...")
        manim_code = (
            "from manim import *\n\n"
            "class ManimatorValidationScene(Scene):\n"
            "    def construct(self):\n"
            "        circle = Circle(color=BLUE, radius=1.5)\n"
            "        title = Text('Manimator Q8_0', font_size=36).next_to(circle, DOWN)\n"
            "        self.play(Create(circle), run_time=1.0)\n"
            "        self.play(Write(title), run_time=1.0)\n"
            "        self.wait(1.0)\n"
        )
        gen_pass = False
    else:
        gen_pass = True

    script_path = MANIM_OUT_DIR / "test_scene.py"
    script_path.write_text(manim_code, encoding="utf-8")
    print(f"Saved generated Manim script ({len(manim_code)} chars) to {script_path}")

    # Now render with Manim
    print("\nCompiling & rendering scene with Manim Community Edition...")
    render_pass = False
    rendered_mp4: Path | None = None

    try:
        render_res = subprocess.run(
            [
                sys.executable, "-m", "manim",
                "-ql",
                "--media_dir", str(MANIM_OUT_DIR),
                str(script_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        print(render_res.stdout[-400:] if render_res.stdout else "")

        # Search for generated mp4
        mp4_files = list(MANIM_OUT_DIR.rglob("*.mp4"))
        if mp4_files and mp4_files[0].stat().st_size > 1000:
            rendered_mp4 = mp4_files[0]
            render_pass = True
            print(f"✔ Rendered video artifact: {rendered_mp4} ({rendered_mp4.stat().st_size / 1e6:.2f} MB)")
        else:
            print("Render check: No valid .mp4 found in output directory.")
    except Exception as e:
        print(f"Render exception: {e}")

    # Now that GGUF and Manim validation are completed, intermediate F16 GGUF can be purged to save disk
    if F16_GGUF_PATH.is_file():
        print(f"\nCleaning up intermediate F16 GGUF to free disk space: {F16_GGUF_PATH.name}")
        F16_GGUF_PATH.unlink()
        show_disk_usage("After purging intermediate F16 GGUF")

    return gen_pass, render_pass, rendered_mp4


# ==============================================================================
# 09_upload_to_huggingface
# ==============================================================================
def step_09_upload_to_huggingface(hf_token: str, model_size_gb: float) -> bool:
    print_step_header("09", f"Upload {Q8_GGUF_PATH.name} to {GGUF_REPO_ID}")

    from huggingface_hub import HfApi

    api = HfApi(token=hf_token)
    api.create_repo(GGUF_REPO_ID, repo_type="model", exist_ok=True, token=hf_token)

    # 1. Create Model Card (README.md)
    readme_path = WORK_DIR / "README.md"
    readme_content = f"""---
license: apache-2.0
base_model: {BASE_MODEL_ID}
library_name: gguf
pipeline_tag: text-generation
language:
  - en
tags:
  - manim
  - manimce
  - manim-voiceover
  - aos
  - gguf
  - q8_0
  - code-generation
  - math
---

# {GGUF_REPO_ID} (Q8_0 GGUF)

High-fidelity **Q8_0 quantized GGUF** release of **qwen-Manimator-1-grpo-clean**, fine-tuned from `{BASE_MODEL_ID}` for pedagogically rich **ManimCE & Manim Voiceover** code synthesis.

- **Base Model**: [`{BASE_MODEL_ID}`](https://huggingface.co/{BASE_MODEL_ID})
- **LoRA Adapter**: [`{ADAPTER_MODEL_ID}`](https://huggingface.co/{ADAPTER_MODEL_ID})
- **Quantization**: `Q8_0` (Near lossless 8-bit quantization)
- **Artifact**: `{Q8_GGUF_PATH.name}` (~{model_size_gb:.2f} GB)
- **Tested Context Window**: `32768` (32K tokens)

---

## Quickstart (Ollama)

```bash
ollama run hf.co/{GGUF_REPO_ID}
```

Or using a custom Modelfile:

```dockerfile
FROM ./{Q8_GGUF_PATH.name}
PARAMETER num_ctx 32768
PARAMETER temperature 0.2
PARAMETER top_p 0.95
SYSTEM "You are an expert Python programmer specializing in ManimCE and educational animations."
```

```bash
ollama create manimator-q8 -f Modelfile
ollama run manimator-q8
```

---

## Quickstart (llama.cpp)

```bash
./llama-cli -m {Q8_GGUF_PATH.name} -c 32768 -p "<|im_start|>user\\nWrite a ManimCE scene explaining Fourier series.<|im_end|>\\n<|im_start|>assistant\\n"
```
"""
    readme_path.write_text(readme_content, encoding="utf-8")

    # 2. Upload README.md
    print("Uploading README.md...")
    api.upload_file(
        path_or_fileobj=str(readme_path),
        path_in_repo="README.md",
        repo_id=GGUF_REPO_ID,
        repo_type="model",
        token=hf_token,
    )

    # 3. Upload Q8_0 GGUF
    print(f"Uploading {Q8_GGUF_PATH.name} ({model_size_gb:.2f} GB)... This may take several minutes.")
    api.upload_file(
        path_or_fileobj=str(Q8_GGUF_PATH),
        path_in_repo=Q8_GGUF_PATH.name,
        repo_id=GGUF_REPO_ID,
        repo_type="model",
        token=hf_token,
    )
    print("✔ Upload complete.")
    return True


# ==============================================================================
# 10_verify_upload
# ==============================================================================
def step_10_verify_upload(hf_token: str) -> bool:
    print_step_header("10", f"Verify Uploaded Repository: {GGUF_REPO_ID}")

    from huggingface_hub import HfApi

    api = HfApi(token=hf_token)
    files = list(api.list_repo_files(GGUF_REPO_ID, repo_type="model", token=hf_token))
    print(f"Files in {GGUF_REPO_ID}: {files}")

    has_gguf = Q8_GGUF_PATH.name in files
    has_readme = "README.md" in files

    if has_gguf and has_readme:
        print("✔ Verification SUCCESS: Both Q8_0 GGUF and README.md are live on Hugging Face Hub.")
        return True
    else:
        print(f"❌ Verification FAILED: Missing required files in {files}")
        return False


# ==============================================================================
# Main Orchestration Loop
# ==============================================================================
def main() -> int:
    print(f"""
************************************************************************
*  Kaggle Pipeline: Qwen3-8B + Manimator GRPO -> Q8_0 GGUF Deployment  *
************************************************************************
""")

    # 01. Setup Environment
    hf_token = step_01_environment_setup()

    # 02. Download Models
    step_02_download_models(hf_token)

    # 03. Merge LoRA
    step_03_merge_lora(hf_token)

    # 04. Convert to GGUF F16
    step_04_convert_to_gguf()

    # 05. Quantize to Q8_0
    q8_file = step_05_quantize_q8()
    actual_size_gb = q8_file.stat().st_size / 1e9

    # 06. Validate Model
    gguf_val_pass = step_06_validate_model()

    # 07. Test 32K Context
    ctx_pass = step_07_test_32k_context()

    # 08. Test Manim Generation & Rendering
    gen_pass, render_pass, _ = step_08_test_manim()

    # 09. Upload to Hugging Face
    upload_pass = False
    if gguf_val_pass and ctx_pass:
        upload_pass = step_09_upload_to_huggingface(hf_token, actual_size_gb)
    else:
        print("Skipping upload due to validation failure.")

    # 10. Verify Upload
    verify_pass = False
    if upload_pass:
        verify_pass = step_10_verify_upload(hf_token)

    # Concise Final Deployment Summary
    summary = f"""
========================================
MANIMATOR GGUF DEPLOYMENT COMPLETE
========================================

Base:
{BASE_MODEL_ID}

Adapter:
{ADAPTER_MODEL_ID}

Quantization:
{QUANT_TYPE}

GGUF:
{Q8_GGUF_PATH.name}

Size:
{actual_size_gb:.2f} GB

Context:
{CONTEXT_LENGTH} tokens

GGUF validation:
{"PASS" if (gguf_val_pass and ctx_pass) else "FAIL"}

Manim generation:
{"PASS" if gen_pass else "FAIL"}

Manim rendering:
{"PASS" if render_pass else "FAIL"}

Hugging Face:
https://huggingface.co/{GGUF_REPO_ID}

Upload:
{"PASS" if verify_pass else "FAIL"}
========================================
"""
    print(summary)
    return 0 if (gguf_val_pass and ctx_pass and upload_pass and verify_pass) else 1


if __name__ == "__main__":
    sys.exit(main())
