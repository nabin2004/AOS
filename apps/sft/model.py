from __future__ import annotations

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    PreTrainedTokenizerBase,
)

from config import TrainingConfig


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


def load_model(config: TrainingConfig) -> torch.nn.Module:
    common_kwargs = {
        "torch_dtype": torch.bfloat16,
        "attn_implementation": config.attn_implementation,
        "device_map": "auto",
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

    freeze_multimodal_towers(model)
    model.gradient_checkpointing_enable()
    return model
