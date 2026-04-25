#   REQUIREMENTS

#   1. Provide a Python runtime with all dependencies installed
#   2. Contain the source code, tests, and data
#   3. Have an entry point that runs the analysis pipeline
#   4. Write outputs to /app/output (which will be mounted as a volume)
#
# Dockerfile below:

FROM python:3.11-slim
LABEL maintainer="Filippo Biagini" \
      description="Investment Risk Assignment Pipeline" \
      version="1.0"

# Python runtime flags for containers: - for isntance do not clutter the image,do not cache wheels in the image, etc..

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install Python dependencies first so this layer is cached
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Create a non-root user to run the pipeline.
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser

# Ensure that all /app content is readable by appuser
COPY --chown=appuser:appuser . .

# Ensure the output directory exists and is writable by appuser - /app/output is the mount point in the file docker-compose.yml.
RUN mkdir -p /app/output && chown -R appuser:appuser /app/output

USER appuser

# Default command runs the pipeline from beginning to end
CMD ["python", "run_analysis.py"]