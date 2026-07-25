"""Demo entry point for the Gemma 4 client.

Requires a running vLLM server, e.g.:

    vllm serve google/gemma-4-31B-it --max-model-len 16384

With a LoRA adapter (see README.md):

    uv run --package server python apps/server/main.py --adapter manim-sft
"""

from __future__ import annotations

import argparse

from gemma4_client import DEFAULT_BASE_MODEL, DEFAULT_LORA_MODULE, Gemma4Client


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Demo the Gemma 4 vLLM client")
    parser.add_argument(
        "--adapter",
        default=None,
        help=f"LoRA module name registered with vLLM (e.g. {DEFAULT_LORA_MODULE})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_BASE_MODEL,
        help="Base model id (effective API model is --adapter when set)",
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
    client = Gemma4Client(model=args.model, adapter=args.adapter)

    if args.list_models:
        for model_id in client.list_models():
            print(model_id)
        return

    print(f"Using model: {client.model}")
    print(client.chat(args.prompt))


if __name__ == "__main__":
    main()
