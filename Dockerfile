# syntax=docker/dockerfile:1

# ---- Base: uv pre-installed ----
FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# ---- Dependencies layer (cached separately from app code) ----
FROM base AS deps
COPY pyproject.toml ./
# If you've committed a uv.lock, copy it too for fully reproducible installs:
# COPY uv.lock ./
RUN uv sync --no-dev --no-install-project

# ---- Final runtime image ----
FROM base AS runtime
RUN groupadd --system app && useradd --system --gid app --no-create-home app

COPY --from=deps /app/.venv /app/.venv
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# No secrets, DB URLs, or API keys are ever baked into this image - every
# value in .env.example is injected at runtime via k8s Secret/env, so the
# same image is safe to promote from dev -> staging -> prod unchanged.
RUN chown -R app:app /app
USER app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/health', timeout=3).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
