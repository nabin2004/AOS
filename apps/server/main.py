"""Demo entry point for the Gemma 4 client.

Requires a running vLLM server, e.g.:

    vllm serve google/gemma-4-31B-it --max-model-len 16384
"""

from gemma4_client import Gemma4Client

if __name__ == "__main__":
    client = Gemma4Client()
    answer = client.chat("Write a short poem about the ocean.")
    print(answer)
