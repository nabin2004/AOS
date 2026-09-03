from __future__ import annotations

import sys

from config import DEFAULT_BETA, DEFAULT_LEARNING_RATE, GRPO_ADAPTER, TrainingConfig
from rewards import combined_reward


def _prompt_token_len(tokenizer, prompt: list) -> int:
    ids = tokenizer.apply_chat_template(
        prompt,
        add_generation_prompt=True,
        tokenize=True,
    )
    return len(ids)


def truncate_dataset_prompts(dataset, tokenizer, max_prompt_length: int):
    from datasets import Dataset

    from manibench import format_user_prompt

    rows = []
    for row in dataset:
        text = row["full_prompt"]
        prompt = format_user_prompt(text)
        while (
            _prompt_token_len(tokenizer, prompt) > max_prompt_length and len(text) > 64
        ):
            text = text[: int(len(text) * 0.9)]
            prompt = format_user_prompt(text)
        if _prompt_token_len(tokenizer, prompt) > max_prompt_length:
            print(
                f"Warning: prompt still {_prompt_token_len(tokenizer, prompt)} tokens "
                f"(limit {max_prompt_length}); problem_id={row.get('problem_id')}",
                file=sys.stderr,
            )
        rows.append({"prompt": prompt, "problem_id": row["problem_id"]})
    return Dataset.from_list(rows)


def max_prompt_token_length(dataset, tokenizer) -> int:
    lengths = [_prompt_token_len(tokenizer, row["prompt"]) for row in dataset]
    return max(lengths) if lengths else 0


def resolve_max_completion_length(
    dataset,
    tokenizer,
    config: TrainingConfig,
    *,
    cap: int | None = None,
) -> int:
    prompt_len = max_prompt_token_length(dataset, tokenizer)
    computed = config.max_seq_length - (prompt_len + 1)
    if computed < 64:
        print(
            f"Warning: max_completion_length={computed} is very small "
            f"(prompt tokens={prompt_len}, max_seq_length={config.max_seq_length}).",
            file=sys.stderr,
        )
        computed = max(computed, 64)
    if cap is not None:
        return min(computed, cap)
    return computed


def make_training_args(
    config: TrainingConfig,
    *,
    max_completion_length: int,
) -> object:
    from trl import GRPOConfig

    common = dict(
        output_dir=str(config.output_dir),
        optim="paged_adamw_8bit",
        loss_type="bnpo",
        mask_truncated_completions=False,
        use_vllm=False,
        report_to=config.report_to,
        run_name=config.run_name,
        bf16=True,
        gradient_checkpointing=True,
        max_completion_length=max_completion_length,
        num_generations=config.num_generations,
        per_device_train_batch_size=config.num_generations,
        gradient_accumulation_steps=1,
        temperature=1.0,
        top_p=0.9,
        beta=config.beta or DEFAULT_BETA,
        warmup_ratio=0.1,
        weight_decay=0.001,
        lr_scheduler_type="linear",
    )

    if config.smoke:
        return GRPOConfig(
            **common,
            max_steps=1,
            learning_rate=config.learning_rate or DEFAULT_LEARNING_RATE,
            logging_steps=1,
            save_strategy="no",
        )

    kwargs: dict = dict(
        **common,
        num_train_epochs=3,
        learning_rate=config.learning_rate or DEFAULT_LEARNING_RATE,
        logging_steps=10,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=2,
    )
    if config.max_steps is not None:
        kwargs["max_steps"] = config.max_steps
        kwargs.pop("num_train_epochs", None)
    return GRPOConfig(**kwargs)


def build_trainer(model, tokenizer, dataset, config: TrainingConfig, training_args):
    from trl import GRPOTrainer

    return GRPOTrainer(
        model=model,
        args=training_args,
        reward_funcs=combined_reward,
        train_dataset=dataset,
        processing_class=tokenizer,
    )


def train_and_save(trainer, model, tokenizer, config: TrainingConfig) -> None:
    trainer.train()
    model.save_pretrained(str(config.output_dir), adapter_name=GRPO_ADAPTER)
    tokenizer.save_pretrained(str(config.output_dir))
    print(f"GRPO LoRA saved to {config.output_dir}")
