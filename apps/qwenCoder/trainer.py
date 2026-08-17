from __future__ import annotations

import torch
from datasets import Dataset
from transformers import PreTrainedTokenizerBase
from trl import SFTTrainer

from config import TrainingConfig, effective_bf16


def _cast_trainable_fp32(model) -> None:
    n = 0
    for param in model.parameters():
        if param.requires_grad and param.dtype != torch.float32:
            param.data = param.data.to(torch.float32)
            n += 1
    if n:
        print(f"Cast {n} trainable tensors to float32 for GradScaler")


def _assert_qlora(model) -> None:
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    frac = trainable / total if total else 0.0
    print(
        f"QLoRA trainable {trainable:,} / {total:,} ({100.0 * frac:.2f}%)"
    )
    if frac > 0.05:
        raise RuntimeError(
            f"Trainable fraction {100.0 * frac:.1f}% > 5%; LoRA did not attach "
            "(this looks like full fine-tuning)."
        )


def build_trainer(
    model,
    tokenizer: PreTrainedTokenizerBase,
    dataset: Dataset,
    config: TrainingConfig,
) -> SFTTrainer:
    # When continuing an existing LoRA, the model is already a PeftModel —
    # do not pass a fresh peft_config (that would create a second adapter).
    peft_config = None if config.init_adapter is not None else config.lora_config()
    trainer = SFTTrainer(
        model=model,
        args=config.sft_config(),
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    use_bf16 = effective_bf16(config.use_bf16)
    trainer.args.bf16 = bool(use_bf16)
    trainer.args.fp16 = bool(not use_bf16)
    # PEFT copies Qwen's BF16 adapter dtype. GradScaler on P100 cannot unscale
    # BF16, and FP16 LoRA raises "Attempting to unscale FP16 gradients."
    _cast_trainable_fp32(trainer.model)
    _assert_qlora(trainer.model)
    print(f"fp16: {trainer.args.fp16}  bf16: {trainer.args.bf16}")
    trainable = {str(p.dtype) for p in trainer.model.parameters() if p.requires_grad}
    print(f"trainable dtypes: {sorted(trainable)}")
    return trainer


def train_and_save(
    trainer: SFTTrainer,
    tokenizer: PreTrainedTokenizerBase,
    config: TrainingConfig,
) -> None:
    trainer.train()
    trainer.save_model(str(config.output_dir))
    tokenizer.save_pretrained(str(config.output_dir))
    print(f"Training complete! Model saved to {config.output_dir}")
    if config.push_to_hub:
        from hub_upload import push_model_folder, require_token

        token = require_token()
        push_model_folder(
            config.output_dir,
            config.hub_model_id,
            token,
            private=config.hub_private,
        )
