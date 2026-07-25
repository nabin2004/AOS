"""Client for Gemma 4 models served through vLLM's OpenAI-compatible API.

Gemma 4 is a multimodal model family (text, image, audio) that adds thinking
mode, tool calling, and structured outputs on top of the standard chat
completions API. This module wraps those capabilities behind a small client
so callers don't need to hand-build request payloads.

The vLLM server itself is launched separately, e.g.:

    vllm serve google/gemma-4-31B-it --max-model-len 16384

LoRA adapters trained in apps/sft are served with --enable-lora and registered
module names (see README.md). Pass adapter="manim-sft" to target a LoRA module.

See README.md for full server launch flags (LoRA, thinking mode, tool calling,
audio, TPU/AMD deployment).
"""

from __future__ import annotations

import json
from typing import Any, NamedTuple

from openai import OpenAI

DEFAULT_BASE_URL = "http://localhost:8000/v1"
DEFAULT_MODEL = "google/gemma-4-31B-it"
DEFAULT_BASE_MODEL = "google/gemma-4-E2B-it"
DEFAULT_LORA_MODULE = "manim-sft"
DEFAULT_ADAPTER_REPO = "nabin2004/AOS-gemma4-manim-sft"
DEFAULT_LORA_RANK = 64

# Per-image token budgets vLLM accepts for Gemma 4's dynamic vision resolution.
VISION_TOKEN_BUDGETS = (70, 140, 280, 560, 1120)

Message = dict[str, Any]


class ThinkingResult(NamedTuple):
    content: str
    reasoning: str | None


def _as_messages(prompt_or_messages: str | list[Message]) -> list[Message]:
    if isinstance(prompt_or_messages, str):
        return [{"role": "user", "content": prompt_or_messages}]
    return prompt_or_messages


def _media_message(prompt: str, media_type: str, urls: list[str]) -> Message:
    url_key = f"{media_type}_url"
    content: list[dict[str, Any]] = [
        {"type": url_key, url_key: {"url": url}} for url in urls
    ]
    content.append({"type": "text", "text": prompt})
    return {"role": "user", "content": content}


class Gemma4Client:
    """Thin wrapper around the OpenAI SDK for a Gemma 4 vLLM server."""

    def __init__(
        self,
        model: str = DEFAULT_BASE_MODEL,
        *,
        adapter: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str = "EMPTY",
    ) -> None:
        self.base_model = model
        self.adapter = adapter
        self.model = adapter or model
        self._client = OpenAI(base_url=base_url, api_key=api_key)

    def list_models(self) -> list[str]:
        """Return model ids exposed by the vLLM /v1/models endpoint."""
        return [entry.id for entry in self._client.models.list().data]

    def chat(
        self,
        prompt_or_messages: str | list[Message],
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Plain text chat completion."""
        response = self._client.chat.completions.create(
            model=self.model,
            messages=_as_messages(prompt_or_messages),
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        return response.choices[0].message.content

    def think(
        self,
        prompt_or_messages: str | list[Message],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> ThinkingResult:
        """Chat completion with thinking mode enabled.

        Requires the server to be launched with --reasoning-parser gemma4.
        """
        response = self._client.chat.completions.create(
            model=self.model,
            messages=_as_messages(prompt_or_messages),
            max_tokens=max_tokens,
            temperature=temperature,
            extra_body={"chat_template_kwargs": {"enable_thinking": True}},
            **kwargs,
        )
        message = response.choices[0].message
        return ThinkingResult(
            content=message.content, reasoning=getattr(message, "reasoning", None)
        )

    def describe_images(
        self,
        image_urls: list[str],
        prompt: str,
        *,
        vision_tokens: int | None = None,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> str:
        """Ask a question about one or more images."""
        if vision_tokens is not None and vision_tokens not in VISION_TOKEN_BUDGETS:
            raise ValueError(
                f"vision_tokens must be one of {VISION_TOKEN_BUDGETS}, got {vision_tokens}"
            )

        extra_body = (
            {"mm_processor_kwargs": {"max_soft_tokens": vision_tokens}}
            if vision_tokens
            else {}
        )
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[_media_message(prompt, "image", image_urls)],
            max_tokens=max_tokens,
            extra_body=extra_body,
            **kwargs,
        )
        return response.choices[0].message.content

    def transcribe_audio(
        self,
        audio_url: str,
        prompt: str = "Provide a verbatim, word-for-word transcription of the audio.",
        *,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> str:
        """Transcribe or answer questions about an audio clip.

        Requires vllm[audio] and a server launched with --limit-mm-per-prompt audio=1.
        Supported by the E2B and E4B model sizes.
        """
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[_media_message(prompt, "audio", [audio_url])],
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.choices[0].message.content

    def describe_video(
        self,
        video_url: str,
        prompt: str,
        *,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> str:
        """Ask a question about a video.

        Requires a server launched with --limit-mm-per-prompt video=1.
        """
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[_media_message(prompt, "video", [video_url])],
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.choices[0].message.content

    def call_with_tools(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
        *,
        max_tokens: int = 1024,
        **kwargs: Any,
    ):
        """Run a chat turn with tool definitions and return the raw message.

        Inspect `message.tool_calls`; if present, append the assistant message
        and a {"role": "tool", "tool_call_id": ..., "content": ...} reply to
        `messages`, then call this again to get the final answer.

        Requires --enable-auto-tool-choice --tool-call-parser gemma4 on the server.
        """
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.choices[0].message

    def structured(
        self,
        prompt_or_messages: str | list[Message],
        schema: dict[str, Any] | type,
        *,
        schema_name: str = "response",
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Chat completion constrained to a JSON schema.

        `schema` accepts either a raw JSON schema dict or a Pydantic model
        class. The schema enforces structure only — put semantic instructions
        (units, formatting) in the prompt itself, since field descriptions
        aren't visible to the model.
        """
        if hasattr(schema, "model_json_schema"):
            schema = schema.model_json_schema()

        response = self._client.chat.completions.create(
            model=self.model,
            messages=_as_messages(prompt_or_messages),
            response_format={
                "type": "json_schema",
                "json_schema": {"name": schema_name, "schema": schema},
            },
            max_tokens=max_tokens,
            **kwargs,
        )
        return json.loads(response.choices[0].message.content)
