
# Build stage
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Install build tools for native extensions (pycairo, manimpango)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config libcairo2-dev libpango1.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv && ln -sf /usr/local/bin/uv /bin/uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy application
COPY . /app

# Install project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# Runtime stage
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Install uv in runtime so Celery worker and agents sub-processes can execute uv commands
COPY --from=builder /usr/local/bin/uv /bin/uv
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /usr/local/bin/uvx /usr/local/bin/uvx
RUN ln -sf /usr/local/bin/uvx /bin/uvx

# System dependencies:
# - ffmpeg, libcairo2, libpango for Manim, audio and media processing
# - nodejs & @llamaindex/liteparse for LiteParse PDF parser
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg git ffmpeg libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    build-essential pkg-config libcairo2-dev libpango1.0-dev \
    texlive-latex-base texlive-fonts-recommended texlive-latex-extra dvisvgm \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @llamaindex/liteparse \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


# Create non-root user and writable directories
RUN adduser --disabled-password --gecos "" appuser && \
    mkdir -p /app/media /app/data /app/chroma_data /app/models_cache

# Copy the complete application once.  ``--chown`` avoids a costly recursive
# ownership walk over the large Manim/Python virtual environment at build time.
COPY --from=builder --chown=appuser:appuser /app /app

# Add venv to path
ENV PATH="/app/.venv/bin:$PATH"
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health')" || exit 1

CMD ["python", "-m", "cli.commands", "server", "run", "--host", "0.0.0.0", "--port", "8000"]
