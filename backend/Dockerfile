# syntax=docker/dockerfile:1.6
# Multi-stage, non-root backend image for CrowdCompass Rover.
# Stage 1 installs the package + dependencies; stage 2 is a slim runtime that
# copies only the installed site-packages and the application source.

# ---- Stage 1: builder -------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml ./
COPY app/ ./app/
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir .

# ---- Stage 2: runtime -------------------------------------------------------
FROM python:3.12-slim AS runtime

# Non-root runtime user.
RUN groupadd -r rover && useradd -r -g rover -u 1000 rover
WORKDIR /app

# Copy installed dependencies and console scripts from the builder.
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
# Copy application source.
COPY --from=builder /build/app ./app

ENV APP_MODE=mock \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER rover
EXPOSE 8000

# Liveness probe hits the public health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
