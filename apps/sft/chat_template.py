from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from transformers import PreTrainedTokenizerBase
from trl.chat_template_utils import get_training_chat_template, has_generation_markers

from config import TrainingConfig

GEMMA4_TURN_MARKER = "<|turn>model"
TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "gemma4_training.jinja"


def is_gemma4_tokenizer(tokenizer: PreTrainedTokenizerBase) -> bool:
    return GEMMA4_TURN_MARKER in (tokenizer.chat_template or "")


def load_gemma4_training_template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def validate_training_template(
    tokenizer: PreTrainedTokenizerBase,
    *,
    require_generation_markers: bool = True,
) -> None:
    """Raise if the chat template is unsafe for Gemma 4 SFT."""
    template = tokenizer.chat_template or ""
    if require_generation_markers and not has_generation_markers(template):
        raise ValueError(
            "Chat template is missing {% generation %} markers required for "
            "assistant_only_loss on Gemma 4. Run prepare_training_tokenizer() "
            "or point inference at an adapter dir that saved the training tokenizer."
        )

    probe = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there."},
    ]
    rendered = tokenizer.apply_chat_template(
        probe,
        tokenize=False,
        add_generation_prompt=False,
    )
    if "<unknown_role>" in rendered:
        raise ValueError(
            "Chat template rendered <unknown_role>. Use assistant roles in data; "
            "the Gemma 4 template maps assistant -> model at render time."
        )
    if "<|turn>model" not in rendered and "assistant" in rendered.lower():
        raise ValueError(
            "Rendered template still contains raw assistant turns instead of "
            "<|turn>model. Check gemma4_training.jinja."
        )


def prepare_training_tokenizer(
    tokenizer: PreTrainedTokenizerBase,
    config: TrainingConfig,
) -> TrainingConfig:
    """Apply TRL or Gemma 4 training template for assistant-only loss."""
    if not config.assistant_only_loss:
        return config

    chat_template = tokenizer.chat_template or ""
    if has_generation_markers(chat_template):
        return config

    try:
        training_template = get_training_chat_template(tokenizer)
    except ValueError:
        if is_gemma4_tokenizer(tokenizer):
            tokenizer.chat_template = load_gemma4_training_template()
            return config

        print(
            "WARNING: No TRL training template for this model. "
            "Disabling assistant_only_loss; training on full sequence."
        )
        return replace(config, assistant_only_loss=False)

    if training_template is not None:
        tokenizer.chat_template = training_template
    return config
