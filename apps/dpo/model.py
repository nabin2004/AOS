from __future__ import annotations

import os

import torch
from peft import PeftModel
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    PreTrainedTokenizerBase,
)

from config import TrainingConfig


def _hub_token() -> str | None:
    return os.environ.get("HF_TOKEN", "").strip() or None


def load_tokenizer(model_id: str) -> PreTrainedTokenizerBase:
    tokenizer = AutoTokenizer.from_pretrained(
        model_id, trust_remote_code=True, token=_hub_token()
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def load_policy_model(config: TrainingConfig):
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

    if config.sft_lora_path is not None and config.sft_lora_path.is_dir():
        print(f"Loading SFT adapter from {config.sft_lora_path}")
        model = PeftModel.from_pretrained(model, str(config.sft_lora_path))
        # Continue training: merge is optional; DPOTrainer + peft_config expects base.
        # Prefer loading SFT as starting point then adding new DPO LoRA via trainer.
        model = model.merge_and_unload()

    return model
