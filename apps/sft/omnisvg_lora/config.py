"""Configuration dataclass for OmniSVG LoRA Fine-Tuning."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class OmniSVGLoRAConfig:
    # Model backbone
    model_name_or_path: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    
    # LoRA hyper-parameters
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    target_modules: List[str] = field(
        default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj"]
    )
    
    # Quantization & Precision
    use_4bit: bool = True
    bnb_4bit_compute_dtype: str = "bfloat16"
    bnb_4bit_quant_type: str = "nf4"
    use_nested_quant: bool = False

    # Training parameters
    output_dir: str = "./omnisvg_lora_output"
    per_device_train_batch_size: int = 4
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    max_grad_norm: float = 0.3
    num_train_epochs: float = 3.0
    warmup_ratio: float = 0.03
    lr_scheduler_type: str = "cosine"
    
    # DeepSpeed ZeRO stage
    use_deepspeed: bool = False
    deepspeed_config: str = "configs/ds_zero2.json"

    # SVG Tokenizer bounds
    canvas_size: int = 200
