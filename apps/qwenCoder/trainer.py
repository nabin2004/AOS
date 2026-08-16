from __future__ import annotations

import torch
from datasets import Dataset
from transformers import PreTrainedTokenizerBase
from trl import SFTTrainer

from config import TrainingConfig, effective_bf16


def _cast_trainable_fp16(model) -> None:
    n = 0
    for param in model.parameters():
        if param.requires_grad and param.dtype == torch.bfloat16:
            param.data = param.data.to(torch.float16)
            n += 1
    if n:
        print(f"Cast {n} trainable tensors from bfloat16 to float16")


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
    if not use_bf16:
        _cast_trainable_fp16(trainer.model)
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
