# syntax=docker/dockerfile:1
FROM python:3.12-slim

# uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# System deps: ffmpeg for moviepy, libgl/glib for opencv
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY . .

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH" \
    SERVER_PORT=8666

EXPOSE 8666

CMD ["python", "main.py"]
