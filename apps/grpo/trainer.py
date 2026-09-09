from __future__ import annotations

import sys

# Compatibility shim for environments with PyTorch < 2.6 where FSDPModule is missing
try:
    import torch.distributed.fsdp as _fsdp
    if not hasattr(_fsdp, "FSDPModule"):
        class FSDPModule: pass
        _fsdp.FSDPModule = FSDPModule
except Exception:
    pass

import torch

from config import DEFAULT_BETA, DEFAULT_LEARNING_RATE, GRPO_ADAPTER, TrainingConfig
from rewards import combined_reward

import time
from transformers import TrainerCallback, TrainerControl, TrainerState, TrainingArguments

class KaggleTimeLimitCallback(TrainerCallback):
    """Stops training cleanly and forces a save/push when time limit is reached."""
    def __init__(self, max_hours: float):
        self.max_hours = max_hours
        self.start_time = time.time()
        
    def on_step_end(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        elapsed_hours = (time.time() - self.start_time) / 3600.0
        if elapsed_hours >= self.max_hours:
            print(f"\n⚠️ Reached time limit ({elapsed_hours:.2f} hrs >= {self.max_hours:.2f} hrs). Forcing save and graceful exit...")
            control.should_save = True
            control.should_training_stop = True


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

    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    use_fp16 = torch.cuda.is_available() and not use_bf16

    common = dict(
        output_dir=str(config.output_dir),
        optim="paged_adamw_8bit",
        loss_type="bnpo",
        mask_truncated_completions=False,
        use_vllm=False,
        report_to=config.report_to,
        run_name=config.run_name,
        bf16=use_bf16,
        fp16=use_fp16,
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
        save_steps=50,
        save_total_limit=2,
        push_to_hub=config.push_to_hub,
        hub_model_id=config.hub_repo,
        hub_strategy="checkpoint",
    )
    if config.max_steps is not None:
        kwargs["max_steps"] = config.max_steps
        kwargs.pop("num_train_epochs", None)

    grpo_config = GRPOConfig(**kwargs)

    # CRITICAL: Prevent HF Trainer from wrapping the 4-bit quantized model in
    # nn.DataParallel on multi-GPU setups. The policy model is pinned to cuda:0
    # via device_map={"":0}, while cuda:1 is reserved for the VLM reward judge.
    # DataParallel tries to replicate quantized weights across GPUs, which causes
    # "CUDA error: illegal memory access" because bitsandbytes NF4 tensors have
    # device-pinned quantization state that cannot be scattered.
    if torch.cuda.device_count() >= 2:
        grpo_config._n_gpu = 1

    return grpo_config


def build_trainer(model, tokenizer, dataset, config: TrainingConfig, training_args):
    from trl import GRPOTrainer

    trainer = GRPOTrainer(
        model=model,
        args=training_args,
        reward_funcs=combined_reward,
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    # Ensure GRPOTrainer generation_config explicitly includes stop tokens (<|im_end|>)
    # so rollouts terminate when the assistant finishes generating instead of running to completion cap!
    if hasattr(trainer, "generation_config") and trainer.generation_config is not None:
        stop_ids = []
        if getattr(tokenizer, "eos_token_id", None) is not None:
            stop_ids.append(tokenizer.eos_token_id)
        try:
            im_end_id = tokenizer.convert_tokens_to_ids("<|im_end|>")
            if im_end_id is not None and im_end_id != getattr(tokenizer, "unk_token_id", None):
                stop_ids.append(im_end_id)
            endoftext_id = tokenizer.convert_tokens_to_ids("<|endoftext|>")
            if endoftext_id is not None and endoftext_id != getattr(tokenizer, "unk_token_id", None):
                stop_ids.append(endoftext_id)
        except Exception:
            pass

        if stop_ids:
            trainer.generation_config.eos_token_id = list(set(stop_ids))
        if getattr(tokenizer, "pad_token_id", None) is not None:
            trainer.generation_config.pad_token_id = tokenizer.pad_token_id

    # Add the Kaggle Time Limit Callback
    if config.max_runtime_hours is not None and config.max_runtime_hours > 0:
        trainer.add_callback(KaggleTimeLimitCallback(max_hours=config.max_runtime_hours))

    return trainer


def train_and_save(trainer, model, tokenizer, config: TrainingConfig) -> None:
    resume_val = None
    if config.resume_from_checkpoint:
        # If the string is "True", cast to boolean True to let HF auto-detect latest checkpoint
        resume_val = True if config.resume_from_checkpoint.lower() == "true" else config.resume_from_checkpoint
    
    trainer.train(resume_from_checkpoint=resume_val)
    model.save_pretrained(str(config.output_dir), adapter_name=GRPO_ADAPTER)
    tokenizer.save_pretrained(str(config.output_dir))
    print(f"GRPO LoRA saved to {config.output_dir}")
