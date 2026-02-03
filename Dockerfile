# ── Builder stage ────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

# Copy only dependency files first (layer caching — deps change rarely)
COPY pyproject.toml uv.lock ./

# Install dependencies into venv (cached unless pyproject.toml/uv.lock change)
RUN uv venv /opt/venv && \
    VIRTUAL_ENV=/opt/venv uv pip install --compile-bytecode -e .

# ── Runtime stage ────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy uv for running alembic migrations via release_command
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"

# Copy application code (changes frequently — separate layer)
COPY pyproject.toml uv.lock ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# Install the project itself (editable, no deps — deps already in venv)
RUN uv pip install --no-deps -e .

# Create non-root user and writable uploads directory
RUN useradd --create-home appuser && \
    mkdir -p /app/app/uploads && \
    chown -R appuser:appuser /app/app/uploads
USER appuser

EXPOSE 8000

# Default command (overridden by fly.worker.toml for Celery)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
