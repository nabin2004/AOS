# Deploying `qwen-Manimator-1-grpo` on RunPod Serverless

This guide outlines the fastest, most cost-effective way to deploy your fine-tuned **`qwen-Manimator-1-grpo`** model to **RunPod Serverless** with OpenAI API compatibility.

---

## 1. Clean Repo vs. Original Repo (Why Clean First?)

Your training repository [`nabin2004/qwen-Manimator-1-grpo`](https://huggingface.co/nabin2004/qwen-Manimator-1-grpo) contains 9 intermediate checkpoint folders (`checkpoint-25`, `checkpoint-50`, ..., `checkpoint-153`, `last-checkpoint`, `ref`), weighing **3.22 GB**.
The actual production adapter files are only **~95 MB**.

RunPod Serverless charges by execution time and disk allocation during container cold starts. Downloading 3.2 GB on every worker boot causes severe latency.

### Step 1: Create the Clean Deploy-Ready Repo

Run the script to extract the root adapter files into a clean Hugging Face repository (`nabin2004/qwen-Manimator-1-grpo-clean`):

```bash
cd apps/qwenCoder
uv run python create_deploy_repo.py --mode adapter
```

*This reduces download size by 97% (~95 MB) and accelerates cold starts by up to 30×.*

---

## 2. Two Deployment Architectures on RunPod

| Architecture | Hugging Face Repo | RunPod vLLM Configuration | Cold Start Speed | Recommendation |
|---|---|---|---|---|
| **Option A: Clean LoRA Adapter** | `nabin2004/qwen-Manimator-1-grpo-clean` (~95 MB) | `MODEL_NAME=Qwen/Qwen3-8B`<br/>`ENABLE_LORA=1`<br/>`LORA_MODULES=manimator=nabin2004/qwen-Manimator-1-grpo-clean` | Fast (pulls base + 95 MB LoRA) | Good if sharing base model |
| **Option B: Merged Standalone** | `nabin2004/qwen-Manimator-1-grpo-merged` (~16 GB) | `MODEL_NAME=nabin2004/qwen-Manimator-1-grpo-merged` | **Fastest & Simplest** (Zero LoRA config) | **⭐ Recommended for Serverless** |

To create the merged standalone model:
```bash
uv run python create_deploy_repo.py --mode merged
```

---

## 3. Step-by-Step RunPod Serverless Setup

1. Log into your [RunPod Console](https://www.runpod.io/console/serverless).
2. Go to **Serverless** -> Click **Quick Deploy**.
3. Choose the official **vLLM** template (`runpod/worker-vllm`).
4. Select GPU:
   - **Recommended**: **L40S (48GB)** or **A40 (48GB)** (~$0.45 - $0.79/hr, active only when processing requests).
5. In **Environment Variables**, paste the configuration:

### Configuration for Merged Model (Recommended)
```env
MODEL_NAME=nabin2004/qwen-Manimator-1-grpo-merged
MAX_MODEL_LEN=32768
HF_TOKEN=your_hf_token_if_private
```

### Configuration for Clean LoRA Adapter
```env
MODEL_NAME=Qwen/Qwen3-8B
ENABLE_LORA=1
LORA_MODULES=manimator=nabin2004/qwen-Manimator-1-grpo-clean
MAX_MODEL_LEN=32768
HF_TOKEN=your_hf_token_if_private
```
*(Note: Do NOT enclose `LORA_MODULES` in brackets `[...]` as a list; vLLM expects `name=path` or a single dictionary mapping `{"name": "...", "path": "..."}`).*

6. Click **Deploy**.

---

## 4. RoPE Scaling (YaRN) for Context Extension

Qwen3-8B natively supports **32,768 tokens**. For Manim generation (planning + scene synthesis), prompt bundles typically stay between 4k and 16k tokens, so **32k native is already plenty**.

However, if you want to extend context to 65k or 131k tokens, add the `ROPE_SCALING` variable:

| Target Context | YaRN Factor | Environment Variable | GPU Requirement |
|---|---|---|---|
| **32,768 (Native)** | None | *(Default; leave ROPE_SCALING unset)* | L40S (48GB) / A40 (48GB) |
| **65,536 ($2\times$)** | `2.0` | `ROPE_SCALING={"rope_type": "yarn", "factor": 2.0, "original_max_position_embeddings": 32768}` | L40S (48GB) / A100 (80GB) |
| **131,072 ($4\times$)** | `4.0` | `ROPE_SCALING={"rope_type": "yarn", "factor": 4.0, "original_max_position_embeddings": 32768}` | A100 (80GB) required |

> [!NOTE]
> Qwen recommends matching the YaRN factor to your actual target context rather than maxing out to 131k unnecessarily, as larger context windows allocate significant VRAM to KV cache and can slightly degrade short-prompt accuracy.

---

## 5. Testing the Deployed Endpoint

Once the endpoint shows **Ready** in the RunPod console, test it via the OpenAI-compatible `/v1/chat/completions` route:

### Python Test Client

```python
import os
from openai import OpenAI

RUNPOD_ENDPOINT_ID = "your-endpoint-id"
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "your-runpod-key")

client = OpenAI(
    api_key=RUNPOD_API_KEY,
    base_url=f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/openai/v1",
)

response = client.chat.completions.create(
    model="manimator",  # or "nabin2004/qwen-Manimator-1-grpo-merged"
    messages=[
        {"role": "system", "content": "You are an expert Manim animation programmer and mathematical educator."},
        {"role": "user", "content": "Create a VoiceoverScene showing three orbiting celestial bodies with synchronized bookmarks."},
    ],
    temperature=0.2,
    max_tokens=2048,
    stream=True,
)

for chunk in response:
    content = chunk.choices[0].delta.content
    if content:
        print(content, end="", flush=True)
```

### cURL Test

```bash
curl -X POST https://api.runpod.ai/v2/<ENDPOINT_ID>/openai/v1/chat/completions \
  -H "Authorization: Bearer <RUNPOD_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "manimator",
    "messages": [
      {"role": "user", "content": "Write a Manim script visualizing Euler'\''s identity with voiceover."}
    ],
    "max_tokens": 1024,
    "temperature": 0.2
  }'
```

---

## 6. Connecting to AOS Application

In your local `apps/ui/aos/.env` or when prompted in the UI:

```env
# Point AOS Coder Agent to RunPod Serverless
CODER_BASE_URL=https://api.runpod.ai/v2/<ENDPOINT_ID>/openai/v1
CODER_API_KEY=<RUNPOD_API_KEY>
CODER_MODEL_NAME=manimator
```
