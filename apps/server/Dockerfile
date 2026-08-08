# GPU vLLM OpenAI-compatible server for AOS merged Gemma 4 31B Manim SFT.
# Slim image: model weights download at runtime into HF_HOME (use a RunPod
# network volume at /workspace so the ~60GB cache persists across pods).
#
# Build (from apps/server):
#   docker build -t aos-vllm:0.26.0 .
#
# Or from repo root:
#   docker build -t aos-vllm:0.26.0 -f apps/server/Dockerfile apps/server

FROM vllm/vllm-openai:v0.26.0

ENV MODEL_ID=nabin2004/AOS-gemma4-31b-manim-merged \
    HOST=0.0.0.0 \
    PORT=8000 \
    MAX_MODEL_LEN=16384 \
    GPU_MEMORY_UTILIZATION=0.90 \
    TENSOR_PARALLEL_SIZE=1 \
    HF_HOME=/workspace/hf-cache \
    HUGGINGFACE_HUB_CACHE=/workspace/hf-cache/hub \
    TRANSFORMERS_CACHE=/workspace/hf-cache/transformers

WORKDIR /app

COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /workspace/hf-cache

EXPOSE 8000

# vLLM exposes /health once the OpenAI API server is up (model load may take minutes).
HEALTHCHECK --interval=30s --timeout=10s --start-period=600s --retries=3 \
    CMD python3 -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8000'), timeout=5)"

ENTRYPOINT ["/app/entrypoint.sh"]
