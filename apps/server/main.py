"""Demo entry point for the Gemma 4 client.

Requires a running inference server, e.g. vLLM:

    vllm serve google/gemma-4-31B-it --max-model-len 16384

With a LoRA adapter (see README.md):

    uv run --package server python apps/server/main.py --adapter manim-sft

With Ollama (after export_gguf.py):

    uv run --package server python apps/server/main.py \\
      --base-url http://localhost:11434/v1 \\
      --model aos-gemma4-31b-manim
"""

from __future__ import annotations

import argparse

from gemma4_client import (
    DEFAULT_BASE_MODEL,
    DEFAULT_BASE_URL,
    DEFAULT_LORA_MODULE,
    DEFAULT_OLLAMA_BASE_URL,
    Gemma4Client,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Demo the Gemma 4 OpenAI client")
    parser.add_argument(
        "--adapter",
        default=None,
        help=f"LoRA module name registered with vLLM (e.g. {DEFAULT_LORA_MODULE})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_BASE_MODEL,
        help="Model id (Ollama tag or HF id; effective API model is --adapter when set)",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"OpenAI-compatible API base URL (Ollama: {DEFAULT_OLLAMA_BASE_URL})",
    )
    parser.add_argument(
        "--api-key",
        default="EMPTY",
        help='API key (use "ollama" for Ollama; vLLM accepts any value)',
    )
    parser.add_argument(
        "--prompt",
        default="Write a short poem about the ocean.",
        help="User prompt for the demo chat completion",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print /v1/models and exit",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    client = Gemma4Client(
        model=args.model,
        adapter=args.adapter,
        base_url=args.base_url,
        api_key=args.api_key,
    )

    if args.list_models:
        for model_id in client.list_models():
            print(model_id)
        return

    print(f"Using model: {client.model}")
    print(client.chat(args.prompt))


if __name__ == "__main__":
    main()
