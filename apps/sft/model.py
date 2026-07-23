from __future__ import annotations

import os
from pathlib import Path

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


def _hub_token() -> str | None:
    token = os.environ.get("HF_TOKEN", "").strip()
    return token or None


def load_tokenizer(model_id: str) -> PreTrainedTokenizerBase:
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=_hub_token())
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


def _load_pretrained_gemma4(model_id: str, **kwargs) -> torch.nn.Module:
    """Load Gemma 4 unified checkpoint; prefer ImageTextToText over CausalLM."""
    try:
        from transformers import AutoModelForImageTextToText

        return AutoModelForImageTextToText.from_pretrained(
            model_id,
            trust_remote_code=True,
            **kwargs,
        )
    except Exception as exc:
        print(
            "WARNING: AutoModelForImageTextToText load failed "
            f"({type(exc).__name__}: {exc}). Falling back to AutoModelForCausalLM."
        )
        return AutoModelForCausalLM.from_pretrained(
            model_id,
            trust_remote_code=True,
            **kwargs,
        )


def load_model(
    config: TrainingConfig, *, for_inference: bool = False
) -> torch.nn.Module:
    if config.use_4bit:
        patch_kbit_training_prep()

    token = _hub_token()
    common_kwargs = {
        "dtype": torch.bfloat16,
        "attn_implementation": config.attn_implementation,
        "device_map": config.device_map,
        "token": token,
    }

    if config.use_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        model = _load_pretrained_gemma4(
            config.model_id,
            quantization_config=bnb_config,
            **common_kwargs,
        )
    else:
        model = _load_pretrained_gemma4(config.model_id, **common_kwargs)

    if config.strip_multimodal_towers:
        strip_multimodal_towers(model)

    freeze_multimodal_towers(model)
    if for_inference:
        model.eval()
    else:
        model.gradient_checkpointing_enable()
    return model


def load_adapter_tokenizer(
    config: TrainingConfig,
    adapter_dir: Path | str,
) -> PreTrainedTokenizerBase:
    adapter_path = Path(adapter_dir)
    tokenizer_source = (
        adapter_path
        if (adapter_path / "tokenizer_config.json").is_file()
        else config.model_id
    )
    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_source), token=_hub_token())
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def load_inference_model(
    config: TrainingConfig,
    adapter_dir: Path | str,
    *,
    validate_template: bool = True,
) -> tuple[torch.nn.Module, PreTrainedTokenizerBase]:
    from peft import PeftModel

    from chat_template import prepare_training_tokenizer, validate_training_template

    adapter_path = Path(adapter_dir)
    if not adapter_path.is_dir():
        raise FileNotFoundError(f"Adapter directory not found: {adapter_path}")
    if not (adapter_path / "adapter_config.json").is_file():
        raise FileNotFoundError(
            f"No adapter_config.json in {adapter_path}. "
            "Point --adapter-dir at the directory saved by run.py."
        )

    tokenizer = load_adapter_tokenizer(config, adapter_path)
    if validate_template:
        prepare_training_tokenizer(tokenizer, config)
        validate_training_template(tokenizer, require_generation_markers=True)

    model = load_model(config, for_inference=True)
    model = PeftModel.from_pretrained(model, str(adapter_path), token=_hub_token())
    model.eval()
    return model, tokenizer
