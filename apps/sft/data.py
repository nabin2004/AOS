from __future__ import annotations

from typing import Any

from datasets import Dataset, load_dataset
from transformers import PreTrainedTokenizerBase

from config import TrainingConfig


def resolve_data_files(config: TrainingConfig) -> str:
    """Return a path or hf:// URL for load_dataset."""
    if config.data_path is not None:
        return str(config.data_path)
    return f"hf://datasets/{config.dataset_repo}/{config.dataset_file}"


def format_trajectory_to_gemma(
    sample: dict[str, Any],
    tokenizer: PreTrainedTokenizerBase,
) -> dict[str, str]:
    """Convert an agent trajectory record into Gemma 4 chat-formatted text."""
    prompt = sample.get("prompt") or sample.get("user_prompt") or ""
    narration = sample.get("narration") or sample.get("summary", "")
    final_code = sample.get("final_code") or ""

    messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]

    for step in sample.get("trajectory") or []:
        messages.append(
            {
                "role": "assistant",
                "content": f"<tool_call>\n{step['input']}\n</tool_call>",
            }
        )
        messages.append({"role": "tool", "content": step["output"]})

    final_content = f"```python\n{final_code}\n```\n\nNarration: {narration}"
    messages.append({"role": "assistant", "content": final_content})

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
        enable_thinking=True,
    )
    return {"text": text}


def _is_trainable_record(sample: dict[str, Any]) -> bool:
    if sample.get("success") is False:
        return False
    final_code = sample.get("final_code")
    return bool(final_code and str(final_code).strip())


def load_training_dataset(
    config: TrainingConfig,
    tokenizer: PreTrainedTokenizerBase,
) -> Dataset:
    data_files = resolve_data_files(config)
    dataset = load_dataset("json", data_files=data_files, split="train")
    dataset = dataset.filter(_is_trainable_record, num_proc=config.num_proc)

    def _format(sample: dict[str, Any]) -> dict[str, str]:
        return format_trajectory_to_gemma(sample, tokenizer)

    return dataset.map(
        _format,
        remove_columns=dataset.column_names,
        num_proc=config.num_proc,
    )
