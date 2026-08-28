"""OmniSVG QLoRA Fine-Tuning Pipeline script.

Configures Qwen2.5-VL / base VLM model with 4-bit quantization, initializes special SVG
tokens, attaches LoRA adapters (r=8, alpha=16), and trains next-token prediction objective.
"""

from __future__ import annotations

import logging
from typing import Tuple, Any

from .config import OmniSVGLoRAConfig

logger = logging.getLogger(__name__)


def setup_model_and_lora(cfg: OmniSVGLoRAConfig) -> Tuple[Any, Any]:
    """Initializes base model with 4-bit quantization and configures LoRA adapters."""
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    except ImportError as e:
        logger.warning(f"PyTorch/Transformers/PEFT not available in current environment: {e}")
        return None, None

    compute_dtype = getattr(torch, cfg.bnb_4bit_compute_dtype)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=cfg.use_4bit,
        bnb_4bit_quant_type=cfg.bnb_4bit_quant_type,
        bnb_4bit_compute_dtype=compute_dtype,
        bnb_4bit_use_double_quant=cfg.use_nested_quant,
    )

    logger.info(f"Loading base model: {cfg.model_name_or_path}")
    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name_or_path, trust_remote_code=True)
    
    # Add custom SVG tokens to vocabulary
    special_tokens = ["<SOP>", "<EOP>", "<EOS>", "<FILL>", "M", "L", "C", "A", "Z"]
    coord_tokens = [f"<C_{i}>" for i in range(cfg.canvas_size * cfg.canvas_size)]
    tokenizer.add_tokens(special_tokens + coord_tokens)

    model = AutoModelForCausalLM.from_pretrained(
        cfg.model_name_or_path,
        quantization_config=bnb_config if cfg.use_4bit else None,
        device_map="auto",
        trust_remote_code=True,
    )
    
    # Resize embeddings for new SVG vocabulary
    model.resize_token_embeddings(len(tokenizer))

    if cfg.use_4bit:
        model = prepare_model_for_kbit_training(model)

    peft_config = LoraConfig(
        r=cfg.lora_r,
        lora_alpha=cfg.lora_alpha,
        target_modules=cfg.target_modules,
        lora_dropout=cfg.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    return model, tokenizer


def train_omnisvg(cfg: OmniSVGLoRAConfig, dataset_manifest_path: str):
    """Run SFT training loop over OmniSVG dataset manifest."""
    model, tokenizer = setup_model_and_lora(cfg)
    if model is None:
        logger.error("Model setup failed due to missing ML dependencies.")
        return

    try:
        from trl import SFTTrainer
        from transformers import TrainingArguments
        from datasets import load_dataset

        dataset = load_dataset("json", data_files=dataset_manifest_path)

        training_args = TrainingArguments(
            output_dir=cfg.output_dir,
            per_device_train_batch_size=cfg.per_device_train_batch_size,
            gradient_accumulation_steps=cfg.gradient_accumulation_steps,
            learning_rate=cfg.learning_rate,
            logging_steps=10,
            num_train_epochs=cfg.num_train_epochs,
            warmup_ratio=cfg.warmup_ratio,
            lr_scheduler_type=cfg.lr_scheduler_type,
            fp16=False,
            bf16=True,
            save_strategy="epoch",
            deepspeed=cfg.deepspeed_config if cfg.use_deepspeed else None,
        )

        trainer = SFTTrainer(
            model=model,
            train_dataset=dataset["train"],
            dataset_text_field="tokens",
            max_seq_length=2048,
            tokenizer=tokenizer,
            args=training_args,
        )

        logger.info("Starting OmniSVG LoRA Fine-Tuning...")
        trainer.train()
        trainer.model.save_pretrained(cfg.output_dir)
        tokenizer.save_pretrained(cfg.output_dir)
        logger.info(f"Model saved to {cfg.output_dir}")
    except Exception as e:
        logger.error(f"Error during SFT training: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = OmniSVGLoRAConfig()
    print("OmniSVG LoRA training module initialized with target modules:", cfg.target_modules)
