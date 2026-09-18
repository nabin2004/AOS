import httpx
import json
import asyncio

class RunPodTransport(httpx.AsyncBaseTransport):
    def __init__(self, underlying):
        self._underlying = underlying

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "runsync" in url_str:
            runsync_idx = url_str.find("/runsync")
            base_runsync_url = url_str[:runsync_idx + len("/runsync")]
            openai_route = url_str[runsync_idx + len("/runsync"):]
            
            if openai_route:
                request.url = httpx.URL(base_runsync_url)
                
                if request.stream:
                    await request.aread()
                    body_bytes = request.content
                    if body_bytes:
                        original_json = json.loads(body_bytes)
                        new_json = {
                            "input": {
                                "openai_route": openai_route,
                                "openai_input": original_json
                            }
                        }
                        # Creating a new stream with the modified content
                        new_body_bytes = json.dumps(new_json).encode("utf-8")
                        
                        request.stream = httpx.ByteStream(new_body_bytes)
                        request.headers["Content-Length"] = str(len(new_body_bytes))
        
        # for testing, just return a fake response
        return httpx.Response(200, json={"choices": [{"message": {"content": "Test success", "role": "assistant"}}]}, request=request)

async def main():
    async with httpx.AsyncClient(transport=RunPodTransport(httpx.AsyncMockTransport(lambda r: httpx.Response(200)))) as client:
        resp = await client.post("https://api.runpod.ai/v2/xyz/runsync/v1/chat/completions", json={"hello": "world"})
        req = resp.request
        print("URL:", req.url)
        await req.aread()
        print("Body:", req.content.decode())

asyncio.run(main())
