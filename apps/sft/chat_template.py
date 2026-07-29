from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from transformers import PreTrainedTokenizerBase
from trl.chat_template_utils import get_training_chat_template, has_generation_markers

from config import TrainingConfig

GEMMA4_TURN_MARKER = "<|turn>model"
QWEN_IM_START = "<|im_start|>"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
GEMMA4_TEMPLATE_PATH = TEMPLATES_DIR / "gemma4_training.jinja"
QWEN_TEMPLATE_PATH = TEMPLATES_DIR / "qwen25_coder_training.jinja"


def is_gemma4_tokenizer(tokenizer: PreTrainedTokenizerBase) -> bool:
    return GEMMA4_TURN_MARKER in (tokenizer.chat_template or "")


def is_qwen_tokenizer(tokenizer: PreTrainedTokenizerBase) -> bool:
    template = tokenizer.chat_template or ""
    return QWEN_IM_START in template or "qwen" in (tokenizer.name_or_path or "").lower()


def load_gemma4_training_template() -> str:
    return GEMMA4_TEMPLATE_PATH.read_text(encoding="utf-8")


def load_qwen_training_template() -> str:
    return QWEN_TEMPLATE_PATH.read_text(encoding="utf-8")


def _tool_probe_messages() -> list[dict]:
    return [
        {"role": "user", "content": "Hello"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_0",
                    "type": "function",
                    "function": {
                        "name": "run_code",
                        "arguments": {"code": "print(1)"},
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_0",
            "name": "run_code",
            "content": "ok",
        },
        {"role": "assistant", "content": "Done."},
    ]


def _rendered_tool_surface_ok(rendered: str) -> bool:
    """True if tool calls/results are visible in the rendered string."""
    has_call = (
        "<tool_call>" in rendered
        or "<|tool_call>" in rendered
        or "run_code" in rendered
    )
    has_response = (
        "<tool_response>" in rendered
        or "<|tool_response>" in rendered
        or ("ok" in rendered and "Done." in rendered)
    )
    return has_call and has_response and "<unknown_role>" not in rendered


def validate_training_template(
    tokenizer: PreTrainedTokenizerBase,
    *,
    require_generation_markers: bool = True,
) -> None:
    """Raise if the chat template is unsafe for assistant-only SFT."""
    template = tokenizer.chat_template or ""
    if require_generation_markers and not has_generation_markers(template):
        raise ValueError(
            "Chat template is missing {% generation %} markers required for "
            "assistant_only_loss. Run prepare_training_tokenizer() "
            "or point inference at an adapter dir that saved the training tokenizer."
        )

    simple = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there."},
    ]
    rendered_simple = tokenizer.apply_chat_template(
        simple,
        tokenize=False,
        add_generation_prompt=False,
    )
    if "<unknown_role>" in rendered_simple:
        raise ValueError(
            "Chat template rendered <unknown_role>. Use assistant roles in data."
        )

    if is_gemma4_tokenizer(tokenizer):
        if "<|turn>model" not in rendered_simple and "assistant" in rendered_simple.lower():
            raise ValueError(
                "Rendered template still contains raw assistant turns instead of "
                "<|turn>model. Check gemma4_training.jinja."
            )

    if is_qwen_tokenizer(tokenizer):
        if "<|im_start|>assistant" not in rendered_simple:
            raise ValueError(
                "Qwen template did not render <|im_start|>assistant. "
                "Check qwen25_coder_training.jinja / TRL training template."
            )

    rendered_tools = tokenizer.apply_chat_template(
        _tool_probe_messages(),
        tokenize=False,
        add_generation_prompt=False,
    )
    if not _rendered_tool_surface_ok(rendered_tools):
        raise ValueError(
            "Chat template dropped tool_calls / tool results (or rendered "
            "<unknown_role>). Fix the training Jinja before SFT — silent tool "
            "elision produces models that never learn CodeMode patterns.\n"
            f"Rendered preview:\n{rendered_tools[:1500]}"
        )


def prepare_training_tokenizer(
    tokenizer: PreTrainedTokenizerBase,
    config: TrainingConfig,
) -> TrainingConfig:
    """Apply TRL or family-specific training template for assistant-only loss."""
    if not config.assistant_only_loss:
        return config

    chat_template = tokenizer.chat_template or ""
    if has_generation_markers(chat_template):
        return config

    training_template: str | None = None
    try:
        training_template = get_training_chat_template(tokenizer)
    except ValueError:
        training_template = None

    if training_template is not None:
        tokenizer.chat_template = training_template
        # TRL can succeed while silently omitting tool branches — verify.
        try:
            validate_training_template(
                tokenizer, require_generation_markers=config.assistant_only_loss
            )
            return config
        except ValueError as exc:
            print(
                f"WARNING: TRL training template failed tool probe ({exc}). "
                "Falling back to a custom training Jinja."
            )

    if is_qwen_tokenizer(tokenizer):
        tokenizer.chat_template = load_qwen_training_template()
        return config

    if is_gemma4_tokenizer(tokenizer):
        tokenizer.chat_template = load_gemma4_training_template()
        return config

    print(
        "WARNING: No TRL training template for this model. "
        "Disabling assistant_only_loss; training on full sequence."
    )
    return replace(config, assistant_only_loss=False)
