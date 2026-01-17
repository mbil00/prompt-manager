# Build stage
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Build wheel
RUN pip install --no-cache-dir build && \
    python -m build --wheel

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (PostgreSQL client libs for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Create data directory for SQLite
RUN mkdir -p /data && chown appuser:appuser /data

# Copy wheel from builder
COPY --from=builder /build/dist/*.whl /tmp/

# Install the application with postgres support
RUN WHEEL=$(ls /tmp/*.whl) && \
    pip install --no-cache-dir "${WHEEL}[postgres]" && \
    rm /tmp/*.whl

# Switch to non-root user
USER appuser

# Environment defaults (secure for production)
ENV PM_HOST=0.0.0.0 \
    PM_PORT=8000 \
    PM_DATABASE_URL=sqlite+aiosqlite:////data/prompts.db \
    PM_ALLOW_LOCALHOST_BYPASS=false \
    PM_LOG_LEVEL=INFO

# Expose port
EXPOSE 8000

# Volume for persistent data
VOLUME ["/data"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the API server
CMD ["pm", "serve"]
