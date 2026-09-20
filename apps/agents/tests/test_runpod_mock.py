import asyncio
import json
import httpx
from openai import AsyncOpenAI
import pytest


class RunPodTransport(httpx.AsyncBaseTransport):
    def __init__(self, underlying: httpx.AsyncBaseTransport):
        self._underlying = underlying

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        is_stream = False

        await request.aread()
        body_bytes = request.content
        if body_bytes:
            try:
                original_json = json.loads(body_bytes)
                is_stream = original_json.get("stream", False)
            except json.JSONDecodeError:
                pass

        # Mock RunPod response
        output_data = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is a neural network.",
                    },
                }
            ],
        }

        if is_stream:
            output_data["object"] = "chat.completion.chunk"
            if "choices" in output_data:
                for choice in output_data["choices"]:
                    if "message" in choice:
                        choice["delta"] = choice.pop("message")
            sse_payload = f"data: {json.dumps(output_data)}\n\ndata: [DONE]\n\n".encode(
                "utf-8"
            )
            stream = httpx.ByteStream(sse_payload)
            headers = [(b"content-type", b"text/event-stream")]
        else:
            unwrapped_body = json.dumps(output_data).encode("utf-8")
            stream = httpx.ByteStream(unwrapped_body)
            headers = [(b"content-type", b"application/json")]

        return httpx.Response(200, headers=headers, stream=stream)


@pytest.mark.asyncio
async def test_runpod_mock_streaming():
    transport = RunPodTransport(httpx.MockTransport(lambda r: httpx.Response(200)))
    client = AsyncOpenAI(
        api_key="fake",
        base_url="https://api.runpod.ai/v2/fake/runsync/v1",
        http_client=httpx.AsyncClient(transport=transport),
    )

    resp = await client.chat.completions.create(
        model="fake",
        messages=[{"role": "user", "content": "hi"}],
        stream=True,
    )
    chunks = []
    async for chunk in resp:
        chunks.append(chunk)
    assert len(chunks) > 0
    assert chunks[0].choices[0].delta.content == "This is a neural network."
