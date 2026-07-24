#!/usr/bin/env python3
"""Run inference with a fine-tuned Gemma 4 LoRA adapter.

By default this mirrors the SFT trajectory distribution: multi-turn tool calling
(CodeMode ``run_code`` + Manim workspace tools) until a final text turn.

Usage (from apps/sft):

    uv run python infer.py --adapter-dir ./gemma4-manim-ft --prompt "Animate a circle."
    uv run python infer.py --adapter-dir /content/gemma4-manim-ft --colab
    uv run python infer.py --adapter-dir ./gemma4-manim-ft --dataset-index 0
    uv run python infer.py --adapter-dir ./gemma4-manim-ft --no-tools  # one-shot smoke
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import torch
from transformers import PreTrainedTokenizerBase

from config import (
    TrainingConfig,
    apply_colab_preset,
    apply_kaggle_preset,
    apply_runpod_preset,
    default_colab_output_dir,
    default_runpod_output_dir,
    is_colab_runtime,
)
from infer_tools import (
    INFER_TOOLS,
    assistant_message_from_generation,
    default_infer_output_dir,
    execute_tool_call,
)
from model import load_inference_model

DEFAULT_PROMPT = (
    "Create a short Manim animation that visualizes gradient descent on a simple "
    "2D loss surface. Include Axes, a moving dot for the iterate, and labeled "
    "update steps."
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Manim code from a fine-tuned Gemma 4 LoRA adapter"
    )
    parser.add_argument(
        "--adapter-dir",
        type=Path,
        default=None,
        help="Directory saved by run.py (default: gemma4-manim-ft or Colab Drive path)",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="User prompt to send to the model",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        default=None,
        help="Read the user prompt from a text file",
    )
    parser.add_argument(
        "--dataset-index",
        type=int,
        default=None,
        help="Use prompt #N from the AOS trajectories dataset on Hugging Face",
    )
    parser.add_argument(
        "--model-id",
        default="google/gemma-4-E2B-it",
        help="Base model id (must match the adapter training run)",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=2048,
        help="Maximum tokens to generate",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature (0 for greedy decoding)",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=0.95,
        help="Top-p nucleus sampling",
    )
    parser.add_argument(
        "--no-4bit",
        action="store_true",
        help="Load base model in BF16 instead of 4-bit",
    )
    parser.add_argument(
        "--device-map",
        default="auto",
        help='Device map ("auto" or GPU index like "0")',
    )
    parser.add_argument(
        "--kaggle",
        action="store_true",
        help="Apply Kaggle-friendly load defaults",
    )
    parser.add_argument(
        "--colab",
        action="store_true",
        help="Apply Colab-friendly load defaults",
    )
    parser.add_argument(
        "--runpod",
        action="store_true",
        help="Apply RunPod-friendly load defaults",
    )
    parser.add_argument(
        "--no-strip-towers",
        action="store_true",
        help="Keep vision/audio towers loaded (uses more VRAM)",
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="One-shot generate without tool definitions or tool loop (debug only)",
    )
    parser.add_argument(
        "--max-tool-rounds",
        type=int,
        default=8,
        help="Max assistant tool-calling rounds before stopping (default: 8)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Coder workspace for manim_write/compile "
            "(default: apps/agents/workspace/infer_runs/<timestamp>)"
        ),
    )
    return parser


def resolve_inference_config(args: argparse.Namespace) -> TrainingConfig:
    config = TrainingConfig(model_id=args.model_id)
    if args.kaggle or __import__("os").environ.get("KAGGLE_KERNEL_RUN_TYPE"):
        config = apply_kaggle_preset(config)
    if args.runpod:
        config = apply_runpod_preset(config)
    if args.colab or is_colab_runtime():
        config = apply_colab_preset(config)
    if args.no_4bit:
        config = replace(config, use_4bit=False)
    if args.no_strip_towers:
        config = replace(config, strip_multimodal_towers=False)
    if args.device_map.isdigit():
        config = replace(config, device_map={"": int(args.device_map)})
    else:
        config = replace(config, device_map=args.device_map)
    return config


def resolve_prompt(args: argparse.Namespace, config: TrainingConfig) -> str:
    if args.prompt_file is not None:
        return args.prompt_file.read_text(encoding="utf-8").strip()
    if args.prompt is not None:
        return args.prompt.strip()
    if args.dataset_index is not None:
        from datasets import load_dataset

        dataset = load_dataset(
            "json",
            data_files=f"hf://datasets/{config.dataset_repo}/{config.dataset_file}",
            split="train",
        )
        row = dataset[args.dataset_index]
        prompt = row.get("user_prompt") or row.get("prompt") or ""
        if not prompt:
            raise ValueError(f"Dataset row {args.dataset_index} has no prompt field")
        return str(prompt).strip()
    return DEFAULT_PROMPT


def _generate_once(
    model: torch.nn.Module,
    tokenizer: PreTrainedTokenizerBase,
    messages: list[dict],
    *,
    tools: list[dict] | None,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
) -> str:
    template_kwargs: dict = {
        "tokenize": True,
        "return_tensors": "pt",
        "return_dict": True,
        "add_generation_prompt": True,
    }
    if tools is not None:
        template_kwargs["tools"] = tools
    model_input = tokenizer.apply_chat_template(messages, **template_kwargs)
    input_ids = model_input["input_ids"]
    attention_mask = model_input.get("attention_mask")
    device = model.get_input_embeddings().weight.device
    input_ids = input_ids.to(device)
    if attention_mask is not None:
        attention_mask = attention_mask.to(device)

    generate_kwargs: dict = {
        "input_ids": input_ids,
        "max_new_tokens": max_new_tokens,
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }
    if attention_mask is not None:
        generate_kwargs["attention_mask"] = attention_mask
    if temperature > 0:
        generate_kwargs.update(
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
        )
    else:
        generate_kwargs["do_sample"] = False

    with torch.inference_mode():
        output_ids = model.generate(**generate_kwargs)

    new_tokens = output_ids[0, input_ids.shape[-1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=False)


def generate_response(
    model: torch.nn.Module,
    tokenizer: PreTrainedTokenizerBase,
    prompt: str,
    *,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
) -> str:
    """One-shot user→assistant generate (no tools). Prefer generate_with_tools."""
    messages = [{"role": "user", "content": prompt}]
    return _generate_once(
        model,
        tokenizer,
        messages,
        tools=None,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
    )


def generate_with_tools(
    model: torch.nn.Module,
    tokenizer: PreTrainedTokenizerBase,
    prompt: str,
    *,
    output_dir: Path,
    max_tool_rounds: int,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
) -> tuple[str, list[dict]]:
    """Multi-turn tool loop matching SFT trajectory formatting.

    Returns (final_assistant_text, full_messages).
    """
    messages: list[dict] = [{"role": "user", "content": prompt}]
    final_text = ""

    for round_idx in range(max_tool_rounds):
        print(f"--- tool round {round_idx + 1}/{max_tool_rounds} ---")
        raw = _generate_once(
            model,
            tokenizer,
            messages,
            tools=INFER_TOOLS,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        assistant = assistant_message_from_generation(raw)
        messages.append(assistant)
        tool_calls = assistant.get("tool_calls") or []
        if not tool_calls:
            final_text = str(assistant.get("content") or raw)
            break

        for tc in tool_calls:
            fn = tc.get("function") or {}
            name = str(fn.get("name") or "unknown")
            arguments = fn.get("arguments") or {}
            print(f"  tool: {name}")
            result = execute_tool_call(name, arguments, output_dir=output_dir)
            preview = result if len(result) <= 400 else result[:400] + "…"
            print(f"  result: {preview}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "name": name,
                    "content": result,
                }
            )
    else:
        # Exhausted rounds while still tool-calling; surface last assistant turn.
        last = messages[-1] if messages else {}
        final_text = str(last.get("content") or "")
        if not final_text and last.get("tool_calls"):
            final_text = (
                f"(stopped after {max_tool_rounds} tool rounds; "
                "last turn still contained tool_calls)"
            )

    return final_text, messages


def default_adapter_dir(args: argparse.Namespace) -> Path:
    if args.adapter_dir is not None:
        return args.adapter_dir
    if args.colab or is_colab_runtime():
        return default_colab_output_dir()
    if args.runpod:
        return default_runpod_output_dir()
    return TrainingConfig().output_dir


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    config = resolve_inference_config(args)
    adapter_dir = (args.adapter_dir or default_adapter_dir(args)).resolve()

    if not adapter_dir.is_dir():
        print(f"ERROR: Adapter directory not found: {adapter_dir}", file=sys.stderr)
        if args.colab or is_colab_runtime():
            print(
                "On Colab, point --adapter-dir at your training output, e.g.\n"
                "  /content/gemma4-manim-ft\n"
                "  /content/drive/MyDrive/gemma4-manim-ft",
                file=sys.stderr,
            )
        return 1

    try:
        prompt = resolve_prompt(args, config)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    output_dir = (args.output_dir or default_infer_output_dir()).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Adapter: {adapter_dir}")
    print(f"Base model: {config.model_id}")
    print(f"Prompt:\n{prompt}\n")
    if args.no_tools:
        print("Mode: one-shot (--no-tools)")
    else:
        print(f"Mode: tool loop (max_rounds={args.max_tool_rounds})")
        print(f"Workspace output_dir: {output_dir}")
    print("Loading model...")

    try:
        model, tokenizer = load_inference_model(config, adapter_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("Generating...\n")
    if args.no_tools:
        response = generate_response(
            model,
            tokenizer,
            prompt,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
        )
        print("=== Assistant response ===")
        print(response)
        return 0

    final_text, messages = generate_with_tools(
        model,
        tokenizer,
        prompt,
        output_dir=output_dir,
        max_tool_rounds=args.max_tool_rounds,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_p=args.top_p,
    )
    n_tools = sum(1 for m in messages if m.get("role") == "tool")
    print(f"\n=== Transcript ({len(messages)} messages, {n_tools} tool results) ===")
    for msg in messages:
        role = msg.get("role")
        if role == "user":
            print(f"[user] {msg.get('content')}")
        elif role == "assistant":
            if msg.get("tool_calls"):
                names = [
                    (tc.get("function") or {}).get("name") for tc in msg["tool_calls"]
                ]
                print(f"[assistant tool_calls] {names}")
                if msg.get("content"):
                    print(msg["content"])
            else:
                print("[assistant]")
                print(msg.get("content") or "")
        elif role == "tool":
            content = str(msg.get("content") or "")
            preview = content if len(content) <= 240 else content[:240] + "…"
            print(f"[tool {msg.get('name')}] {preview}")
    print("\n=== Final assistant text ===")
    print(final_text)
    print(f"\nWorkspace: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
