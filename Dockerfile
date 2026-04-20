FROM python:3.13-slim

# Install uv from its official image — no apt dependencies needed
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# ── Layer 1: dependencies (cached until pyproject.toml or uv.lock changes) ──
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ── Layer 2: project source + tests ─────────────────────────────────────────
COPY src/ ./src/
COPY tests/ ./tests/
COPY run_analysis.py setup_check.py ./
RUN uv sync --frozen --no-dev

# ── Layer 3: data (changes most frequently — keep last for cache efficiency) ─
COPY data/ ./data/

RUN mkdir -p output

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "run_analysis.py", "--output-dir", "/app/output"]
