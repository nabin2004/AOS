# Use the latest vLLM release for full Qwen3 YaRN support
FROM vllm/vllm-openai:v0.7.3



# Expose port 8000 for the vLLM OpenAI-compatible server
EXPOSE 8000

# Start vLLM with the model, YaRN context scaling, and the LoRA adapter enabled.
# Factor 2.0 scales the native 32k context to 65k.
# Option 1 (Recommended): Load the merged weights directly for maximum throughput & fastest boot:
# CMD [ \
#     "--model", "nabin2004/qwen-Manimator-1-grpo-merged", \
#     "--host", "0.0.0.0", \
#     "--port", "8000", \
#     "--max-model-len", "65536", \
#     "--rope-scaling", "{\"rope_type\":\"yarn\",\"factor\":2.0,\"original_max_position_embeddings\":32768}", \
#     "--gpu-memory-utilization", "0.90", \
#     "--max-num-seqs", "128" \
# ]

# Option 2: Dynamic LoRA on top of base model
CMD [ \
    "--model", "Qwen/Qwen3-8B", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--max-model-len", "65536", \
    "--rope-scaling", "{\"rope_type\":\"yarn\",\"factor\":2.0,\"original_max_position_embeddings\":32768}", \
    "--gpu-memory-utilization", "0.90", \
    "--max-num-seqs", "128", \
    "--enable-lora", \
    "--lora-modules", "{\"name\": \"manimator\", \"path\": \"nabin2004/qwen-Manimator-1-grpo-clean\", \"base_model_name\": \"Qwen/Qwen3-8B\"}" \
]

