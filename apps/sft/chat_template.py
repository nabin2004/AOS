from __future__ import annotations

from dataclasses import replace

from transformers import PreTrainedTokenizerBase
from trl.chat_template_utils import get_training_chat_template, has_generation_markers

from config import TrainingConfig


def prepare_training_tokenizer(
    tokenizer: PreTrainedTokenizerBase,
    config: TrainingConfig,
) -> TrainingConfig:
    """Apply TRL training template when supported; otherwise disable assistant-only loss."""
    if not config.assistant_only_loss:
        return config

    chat_template = tokenizer.chat_template or ""
    if has_generation_markers(chat_template):
        return config

    try:
        training_template = get_training_chat_template(tokenizer)
    except ValueError:
        print(
            "WARNING: No TRL training template for this model (e.g. Gemma 4). "
            "Disabling assistant_only_loss; training on full sequence."
        )
        return replace(config, assistant_only_loss=False)

    if training_template is not None:
        tokenizer.chat_template = training_template
    return config
