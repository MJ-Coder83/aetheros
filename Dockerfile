# InkosAI Production Dockerfile
# Multi-stage build for optimized production image

# Stage 1: Builder
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv pip install --system --no-cache -r pyproject.toml

# Stage 2: Production
FROM python:3.13-slim AS production

WORKDIR /app

# Security: Create non-root user
RUN groupadd -r inkosai && useradd -r -g inkosai inkosai

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=inkosai:inkosai packages/ ./packages/
COPY --chown=inkosai:inkosai services/ ./services/
COPY --chown=inkosai:inkosai tests/ ./tests/

# Switch to non-root user
USER inkosai

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Run the API server
CMD ["python", "-m", "uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
