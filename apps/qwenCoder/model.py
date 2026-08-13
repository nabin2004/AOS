from __future__ import annotations

import os

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    PreTrainedTokenizerBase,
)

from config import TrainingConfig


def _hub_token() -> str | None:
    token = os.environ.get("HF_TOKEN", "").strip()
    return token or None


def load_tokenizer(model_id: str) -> PreTrainedTokenizerBase:
    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        token=_hub_token(),
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def load_model(config: TrainingConfig):
    kwargs: dict = {
        "trust_remote_code": True,
        "token": _hub_token(),
        "device_map": "auto",
        "torch_dtype": torch.bfloat16,
    }
    if config.use_4bit:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

    model = AutoModelForCausalLM.from_pretrained(config.model_id, **kwargs)
    model.config.use_cache = False

    if config.init_adapter is not None:
        from peft import PeftModel

        adapter = config.init_adapter
        if not adapter.is_dir():
            raise FileNotFoundError(f"init-adapter not found: {adapter}")
        print(f"Continuing from adapter: {adapter}")
        model = PeftModel.from_pretrained(
            model,
            str(adapter),
            is_trainable=True,
        )

    return model
