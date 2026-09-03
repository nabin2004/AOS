---
license: mit
task_categories:
- text-generation
- text-to-speech
language:
- en
tags:
- manim
- manim-voiceover
- educational-video
- synthetic-dataset
- aos
size_categories:
- n<1K
---

# AOS-Narrated-Manim-400

This dataset contains **400 executable `manim-voiceover` scripts** converted from standard Manim Community Edition (CE) trajectories using Gemini 2.5 Flash Batch API.

## Dataset Summary

- **Total Samples:** 400
- **Format:** JSON Lines (`jsonl`)
- **Key Fields:**
  - `id`: Sample identifier
  - `narrated_manim_code`: Executable Python scene code inheriting from `VoiceoverScene` with `self.voiceover(...)` blocks and phonetic mathematical narration.
  - `status`: Conversion status (`success` / `failed`)

## Conversion Pipeline Details

1. **System Contract:** Enforces `VoiceoverScene` inheritance, initial `self.set_speech_service(GTTSService())` initialization, and phonetic expression of LaTeX symbols in spoken text.
2. **Timing Synchronization:** All visual animations inside `with self.voiceover(...) as tracker:` use `run_time=tracker.duration`.
3. **Engine:** Converted via asynchronous Google Gemini 2.5 Flash Batch API.

## Usage

```python
from datasets import load_dataset

dataset = load_dataset("nabin2004/AOS-Narrated-Manim-400")
print(dataset["train"][0]["narrated_manim_code"])
```

## AOS Platform Integration

Created for the **AOS (Agentic Orchestration System)** project fine-tuning pipelines.
