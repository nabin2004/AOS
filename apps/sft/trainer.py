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
    trainer = SFTTrainer(
        model=model,
        args=config.sft_config(),
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=config.lora_config(),
    )
    if config.eval_manibench:
        import sys
        from pathlib import Path
        training_root = Path(__file__).resolve().parent.parent / "training"
        if str(training_root) not in sys.path:
            sys.path.insert(0, str(training_root))
        try:
            from manibench_callback import ManiBenchEvalCallback
            trainer.add_callback(
                ManiBenchEvalCallback(
                    render=config.manibench_render,
                    timeout=config.manibench_timeout,
                )
            )
            print("Attached ManiBenchEvalCallback for epoch evaluation")
        except Exception as exc:
            print(f"WARNING: Could not attach ManiBenchEvalCallback ({exc})")
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
