# ── Stage 1: build dependencies ────────────────────────────────────
# We use python:3.11-slim as the base image.
#
# WHY SLIM?
#   'slim' is a stripped-down Debian image with Python pre-installed.
#   It is much smaller than the full Debian image (~150MB vs ~900MB),
#   which means faster builds and less surface for security vulnerabilities.
#
# LAYER ORDER MATTERS for caching:
#   Docker caches each instruction. If a layer hasn't changed, it reuses
#   the cached version. We copy requirements.txt FIRST (before source code)
#   so that pip install is only re-run when dependencies change —
#   not every time we edit a Python file.
FROM python:3.11-slim

# Set the working directory inside the container.
# All subsequent COPY / RUN / CMD paths are relative to this.
WORKDIR /app

# Install system dependencies needed by some Python packages.
# --no-install-recommends keeps the install minimal.
# We clean up apt cache in the same RUN layer to avoid bloating the image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy ONLY requirements first — this layer is cached until requirements.txt changes.
COPY requirements.txt .

# Install Python dependencies.
# --no-cache-dir avoids storing the pip download cache in the image (saves space).
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the project.
# We copy source code AFTER pip install so code changes don't bust the pip cache.
COPY src/ ./src/
COPY data/ ./data/
COPY run_analysis.py .
COPY tests/ ./tests/
COPY pyproject.toml .

# Create the output directory.
# In production this will be overridden by the Docker volume mount,
# but it needs to exist in the image too.
RUN mkdir -p output

# ── Security: run as non-root user ──────────────────────────────────
# Containers running as root are a security risk.
# We create a dedicated non-root user 'riskuser' and switch to it.
# chown ensures the app directory is owned by riskuser.
RUN useradd --create-home --shell /bin/bash riskuser \
    && chown -R riskuser:riskuser /app
USER riskuser

# The command that runs when the container starts.
CMD ["python", "run_analysis.py"]
