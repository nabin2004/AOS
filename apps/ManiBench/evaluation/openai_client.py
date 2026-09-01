"""
ManiBench Evaluation — OpenAI-Compatible API Client
=====================================================
Handles LLM code generation via any OpenAI-compatible chat completions API
(vLLM, LocalAI, LM Studio, Ollama OpenAI mode, etc.).

Auth: optional Bearer <OPENAI_API_KEY> (local servers often need none).

Uses httpx for reliable timeout enforcement.
"""

import time
import re
from typing import Any
import httpx

from evaluation.config import (
    OPENAI_API_KEY,
    MAX_RETRIES,
    RETRY_DELAY,
    ModelSpec,
)

# Hard timeout: (connect, read, write, pool) — all in seconds
HTTPX_TIMEOUT = httpx.Timeout(10.0, read=120.0, write=30.0, pool=10.0)


class OpenAICompatibleError(Exception):
    """Raised on unrecoverable OpenAI-compatible API errors."""
    pass


class OpenAICompatibleClient:
    """
    Stateless client for OpenAI-compatible chat completions (e.g. vLLM).

    Usage:
        client = OpenAICompatibleClient(base_url="http://localhost:8000/v1")
        result = client.generate(model_spec, messages)
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
    ):
        base_url = (base_url or "").rstrip("/")
        if not base_url:
            raise OpenAICompatibleError(
                "base_url is required for the openai provider. "
                "Pass --base-url or set OPENAI_BASE_URL "
                "(e.g. http://localhost:8000/v1)."
            )
        self.base_url = base_url
        # Empty string means unauthenticated (common for local vLLM)
        self.api_key = api_key if api_key is not None else OPENAI_API_KEY

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def generate(
        self,
        model: ModelSpec,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """
        Send a chat completion request and return parsed result.

        Returns:
            {
                "content": str,          # Generated text
                "code": str,             # Extracted Python code block
                "prompt_tokens": int,
                "completion_tokens": int,
                "total_tokens": int,
                "latency_ms": float,
                "model_id": str,
                "finish_reason": str,
            }
        """
        payload = {
            "model": model.id,
            "messages": messages,
            "temperature": temperature if temperature is not None else model.temperature,
            "max_tokens": max_tokens or model.max_tokens,
            "top_p": model.top_p,
            "stream": False,
        }

        headers = self._headers()

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                t0 = time.monotonic()
                with httpx.Client(timeout=HTTPX_TIMEOUT) as client:
                    resp = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                latency_ms = (time.monotonic() - t0) * 1000

                if resp.status_code in (429, 502, 503):
                    wait = RETRY_DELAY * attempt
                    last_error = OpenAICompatibleError(
                        f"HTTP {resp.status_code}: {resp.text[:500]}"
                    )
                    if attempt < MAX_RETRIES:
                        time.sleep(wait)
                        continue
                    raise last_error

                if resp.status_code != 200:
                    error_body = resp.text[:500]
                    raise OpenAICompatibleError(
                        f"HTTP {resp.status_code}: {error_body}"
                    )

                data = resp.json()

                choices = data.get("choices", [])
                if not choices:
                    raise OpenAICompatibleError(
                        f"No choices in API response: {str(data)[:300]}"
                    )

                choice = choices[0]
                message = choice.get("message", {})
                if isinstance(message, str):
                    content = message
                else:
                    content = message.get("content", "")
                usage = data.get("usage", {})

                return {
                    "content": content,
                    "code": self._extract_code(content),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "latency_ms": latency_ms,
                    "model_id": data.get("model", model.id),
                    "finish_reason": choice.get("finish_reason", "unknown"),
                }

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                continue
            except httpx.ConnectError as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                continue

        raise OpenAICompatibleError(
            f"Failed after {MAX_RETRIES} attempts: {last_error}"
        )

    @staticmethod
    def _extract_code(content: str) -> str:
        """
        Extract Python code from LLM response.

        Handles:
          - ```python ... ``` blocks
          - ``` ... ``` blocks
          - Raw code (if no code fence found)
        """
        pattern = r"```python\s*\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)
        if matches:
            return max(matches, key=len).strip()

        pattern = r"```\s*\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)
        if matches:
            return max(matches, key=len).strip()

        lines = content.split("\n")
        code_start = None
        for i, line in enumerate(lines):
            if "from manim import" in line or "import manim" in line:
                code_start = i
                break

        if code_start is not None:
            return "\n".join(lines[code_start:]).strip()

        return content.strip()

    def list_models(self) -> list[dict]:
        """Fetch available models from the OpenAI-compatible /models endpoint."""
        with httpx.Client(timeout=HTTPX_TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/models",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
