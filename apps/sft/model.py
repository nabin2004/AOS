from __future__ import annotations

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    PreTrainedTokenizerBase,
)

from config import TrainingConfig

_MULTIMODAL_TOWER_ATTRS = (
    "vision_tower",
    "embed_vision",
    "audio_tower",
    "embed_audio",
)


def load_tokenizer(model_id: str) -> PreTrainedTokenizerBase:
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def freeze_multimodal_towers(model: torch.nn.Module) -> None:
    """Gemma 4 E2B/E4B: train only the language model backbone."""
    for name, param in model.named_parameters():
        if not name.startswith("model.language_model"):
            param.requires_grad = False


def strip_multimodal_towers(model: torch.nn.Module) -> None:
    """Drop unused vision/audio modules to reduce VRAM for text-only SFT."""
    inner = getattr(model, "model", None)
    if inner is None:
        return

    removed: list[str] = []
    for attr in _MULTIMODAL_TOWER_ATTRS:
        if hasattr(inner, attr):
            delattr(inner, attr)
            removed.append(attr)

    if removed:
        print(f"Stripped multimodal towers: {', '.join(removed)}")


def patch_kbit_training_prep() -> None:
    """Skip fp32 embedding upcast that can OOM Gemma 4 on small GPUs."""
    import peft.utils.other as peft_other

    if getattr(peft_other, "_aos_kbit_patch_applied", False):
        return

    def _noop(model, *args, **kwargs):
        return model

    peft_other.prepare_model_for_kbit_training = _noop
    peft_other._aos_kbit_patch_applied = True


def load_model(config: TrainingConfig) -> torch.nn.Module:
    if config.use_4bit:
        patch_kbit_training_prep()

    common_kwargs = {
        "torch_dtype": torch.bfloat16,
        "attn_implementation": config.attn_implementation,
        "device_map": config.device_map,
    }

    if config.use_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        model = AutoModelForCausalLM.from_pretrained(
            config.model_id,
            quantization_config=bnb_config,
            **common_kwargs,
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            config.model_id,
            **common_kwargs,
        )

    if config.strip_multimodal_towers:
        strip_multimodal_towers(model)

    freeze_multimodal_towers(model)
    model.gradient_checkpointing_enable()
    return model
