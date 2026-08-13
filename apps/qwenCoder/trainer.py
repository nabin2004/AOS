from __future__ import annotations

from datasets import Dataset
from transformers import PreTrainedTokenizerBase
from trl import SFTTrainer

from config import TrainingConfig


def build_trainer(
    model,
    tokenizer: PreTrainedTokenizerBase,
    dataset: Dataset,
    config: TrainingConfig,
) -> SFTTrainer:
    # When continuing an existing LoRA, the model is already a PeftModel —
    # do not pass a fresh peft_config (that would create a second adapter).
    peft_config = None if config.init_adapter is not None else config.lora_config()
    return SFTTrainer(
        model=model,
        args=config.sft_config(),
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )


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
