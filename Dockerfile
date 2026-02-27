# ============================================================
# Stage 1: Builder - Install dependencies
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy source code first
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY pyproject.toml ./

# Install uv for faster package management
RUN pip install uv

# Install dependencies and package
RUN uv sync --no-dev && \
    uv pip install -e .

# ============================================================
# Stage 2: Production - Minimal runtime image
# ============================================================
FROM python:3.11-slim AS production

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# Copy installed packages from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/src /app/src
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/alembic.ini /app/alembic.ini

# Set virtual environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app"

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)" || exit 1

# Run server directly (skip alembic - run manually after)
CMD ["uvicorn", "nova_guard.main:app", "--host", "0.0.0.0", "--port", "8000"]
