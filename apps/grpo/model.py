from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Compatibility shim for environments with PyTorch < 2.6 where FSDPModule is missing
try:
    import torch.distributed.fsdp as _fsdp
    if not hasattr(_fsdp, "FSDPModule"):
        class FSDPModule: pass
        _fsdp.FSDPModule = FSDPModule
except Exception:
    pass

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from config import (
    DEFAULT_BASE_MODEL,
    GRPO_ADAPTER,
    TrainingConfig,
    hub_token,
)


def check_cuda_or_exit() -> None:
    if not torch.cuda.is_available():
        print(
            "CUDA is required for GRPO. Run on an NVIDIA GPU server:\n"
            "  cd apps/grpo && uv sync && uv run python run.py --smoke",
            file=sys.stderr,
        )
        raise SystemExit(1)


def _grpo_lora_config():
    from peft import LoraConfig, TaskType

    return LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )


def _base_model_for_adapter(adapter_path: Path | str, fallback: str) -> str:
    local = Path(adapter_path)
    if local.is_dir():
        cfg_path = local / "adapter_config.json"
        if cfg_path.is_file():
            with cfg_path.open(encoding="utf-8") as f:
                return json.load(f).get("base_model_name_or_path", fallback)
        return fallback

    from huggingface_hub import hf_hub_download

    try:
        cfg_path = Path(
            hf_hub_download(
                str(adapter_path),
                "adapter_config.json",
                token=hub_token(),
            ),
        )
        with cfg_path.open(encoding="utf-8") as f:
            return json.load(f).get("base_model_name_or_path", fallback)
    except Exception:
        return fallback


def _load_qwen(config: TrainingConfig):
    """Qwen path: transformers CausalLM + PEFT (no Unsloth FastVisionModel)."""
    from peft import PeftModel, get_peft_model

    default_fallback = "Qwen/Qwen3-8B"
    if config.grpo_only:
        base = config.base_model or default_fallback
    else:
        base = config.base_model or _base_model_for_adapter(
            config.sft_lora_path,
            default_fallback,
        )

    token = hub_token()

    # Hardware compute dtype selection: bf16 if supported (Ampere+), fp16 for Turing (T4)
    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    compute_dtype = torch.bfloat16 if use_bf16 else torch.float16

    kwargs: dict = {
        "trust_remote_code": True,
        "token": token,
        "device_map": "auto",
        "torch_dtype": compute_dtype,
    }
    if config.load_in_4bit:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True,
        )

    tokenizer = AutoTokenizer.from_pretrained(base, trust_remote_code=True, token=token)
    im_end_id = tokenizer.convert_tokens_to_ids("<|im_end|>")
    endoftext_id = tokenizer.convert_tokens_to_ids("<|endoftext|>")
    if im_end_id is not None and im_end_id != getattr(tokenizer, "unk_token_id", None):
        tokenizer.eos_token = "<|im_end|>"
        tokenizer.eos_token_id = im_end_id
    if endoftext_id is not None and endoftext_id != getattr(tokenizer, "unk_token_id", None):
        tokenizer.pad_token = "<|endoftext|>"
        tokenizer.pad_token_id = endoftext_id
    elif tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    model = AutoModelForCausalLM.from_pretrained(base, **kwargs)
    model.config.use_cache = False
    grpo_config = _grpo_lora_config()

    if config.grpo_only or not config.sft_lora_path:
        model = get_peft_model(model, grpo_config, adapter_name=GRPO_ADAPTER)
    elif config.stack_lora:
        # Stacked mode: load initial DPO adapter frozen under 'sft', add new trainable 'default' adapter
        print(f"Stacking new LoRA adapter on top of frozen adapter: {config.sft_lora_path}")
        model = PeftModel.from_pretrained(
            model,
            str(config.sft_lora_path),
            adapter_name="sft",
            token=token,
        )
        for name, param in model.named_parameters():
            if "sft" in name:
                param.requires_grad = False
        model.add_adapter(GRPO_ADAPTER, grpo_config)
        model.set_adapter(GRPO_ADAPTER)
    else:
        # Continual mode (default): load DPO adapter directly as trainable policy adapter
        print(f"Loading initial policy adapter from DPO checkpoint: {config.sft_lora_path} (is_trainable=True)")
        model = PeftModel.from_pretrained(
            model,
            str(config.sft_lora_path),
            is_trainable=True,
            adapter_name=GRPO_ADAPTER,
            token=token,
        )

    model.train()
    return model, tokenizer


def _load_gemma(config: TrainingConfig):
    from peft import PeftModel, get_peft_model
    from unsloth import FastVisionModel

    if config.grpo_only:
        base = config.base_model or DEFAULT_BASE_MODEL
    else:
        base = config.base_model or _base_model_for_adapter(
            config.sft_lora_path,
            DEFAULT_BASE_MODEL,
        )
    token = hub_token()

    model, tokenizer = FastVisionModel.from_pretrained(
        model_name=base,
        max_seq_length=config.max_seq_length,
        load_in_4bit=config.load_in_4bit,
        fast_inference=False,
        token=token,
    )
    if getattr(tokenizer, "pad_token", None) is None:
        tokenizer.pad_token = tokenizer.eos_token

    grpo_config = _grpo_lora_config()
    sft_path = str(config.sft_lora_path)

    if config.grpo_only or not config.sft_lora_path:
        model = get_peft_model(model, grpo_config, adapter_name=GRPO_ADAPTER)
    elif config.stack_lora:
        model = PeftModel.from_pretrained(
            model,
            sft_path,
            adapter_name="sft",
            token=token,
        )
        for name, param in model.named_parameters():
            if "sft" in name:
                param.requires_grad = False
        model.add_adapter(GRPO_ADAPTER, grpo_config)
        model.set_adapter(GRPO_ADAPTER)
    else:
        model = PeftModel.from_pretrained(
            model,
            sft_path,
            is_trainable=True,
            adapter_name=GRPO_ADAPTER,
            token=token,
        )

    model.train()
    return model, tokenizer


def load_model(config: TrainingConfig):
    if config.base_family == "qwen":
        return _load_qwen(config)
    return _load_gemma(config)
