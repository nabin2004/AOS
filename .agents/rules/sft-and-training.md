# SFT, DPO, and Model Training Guidelines

## Training Traces & Data Generation
- Traces from the Code Agent are stored in `workspace/coder_runs/*/traces/` and appended to `training_data/trajectories.jsonl`.
- Always verify `"compile_ok": true` and prefer trajectories with `has_audio=true` for highest quality SFT datasets.
- Use `apps/agents/export_local_sft.py` to convert raw trajectories into tool-use JSONL formats (`export_traces/coder_sft/tool_trace*.jsonl`).

## Fine-Tuning & Quantization
- **Phase 1 SFT**: `apps/sft/run.py` fine-tunes LLMs on Manim trajectory data.
- **Preference Optimization (DPO/GRPO)**: `apps/dpo` and `apps/grpo` contain RL/preference optimization code.
- **GGUF & Ollama Export**: Use `apps/sft/export_gguf.py` to produce GGUF models for local Ollama serving.
- Model cards and Modelfiles reside in `apps/sft/templates/`.
