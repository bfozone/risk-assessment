# Docker Setup

`docker compose up --build` builds the image, runs the analysis pipeline, and writes all outputs to `./output/` on the host.

```
docker compose up --build          # run analysis → ./output/
docker compose run --rm tests      # run test suite
```

---

## Dockerfile walkthrough

### Base image — `python:3.13-slim`

`slim` is the Debian-based image with the CPython interpreter and nothing else — no build tools, no extras. It is the standard choice when the application has no compiled C extensions that require a full build environment at runtime. `alpine` would be smaller but its musl libc causes subtle incompatibilities with wheels built for glibc (numpy, pandas, scipy all ship glibc wheels); the size saving is not worth the friction.

### uv installation

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
```

uv is copied as a single static binary from the official image. No `apt-get` or `pip install uv` needed — keeps the layer small and the installation reproducible at a pinned upstream digest.

### Layer ordering

```dockerfile
# Layer 1 — dependencies only (lockfile-stable)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Layer 2 — project source (changes on every code edit)
COPY src/ ./src/
...
RUN uv sync --frozen --no-dev

# Layer 3 — data (changes most frequently)
COPY data/ ./data/
```

Docker cache invalidates all layers below a changed `COPY`. Separating slow operations (dependency resolution, ~100 packages) from fast ones (project install, data copy) means:

- editing source code → only Layer 2 and below re-run; Layer 1 is cached
- updating data → only Layer 3 re-runs; both dependency layers are cached
- changing `pyproject.toml` / `uv.lock` → full rebuild (correct, since deps changed)

`--no-install-project` on the first sync tells uv to install third-party packages only, deferring the project itself until its source code is present in Layer 2.

### `--frozen` flag

Requires uv to use `uv.lock` exactly as written and refuse to update it. This makes the build deterministic: the same image is produced on every machine and in CI regardless of what newer package versions are available upstream.

### `--no-dev` flag

Excludes the `[dependency-groups] dev` packages (jupyterlab, ruff, pytest, debugpy, ~30 packages). The production image only contains what the analysis pipeline needs at runtime.

### Virtual environment activation

```dockerfile
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "run_analysis.py", "--output-dir", "/app/output"]
```

`uv sync` creates a standard `.venv` inside `/app`. Setting `VIRTUAL_ENV` and prepending its `bin/` to `PATH` activates it for all subsequent commands and for the final `CMD` without going through `uv run`. This avoids a runtime sync: `uv run` would re-resolve and potentially re-download packages on every container start; invoking `python` directly from the activated venv skips that entirely.

### No non-root user

A dedicated non-root user (`useradd -m appuser`) is the standard hardening practice for production images. It is not configured here because this container's only purpose is writing to a bind-mounted host directory (`./output`); adding a non-root user would require either matching UIDs between the container and the host or adding `chmod`/`chown` steps that complicate the setup without a meaningful security benefit for a local analysis workload.

---

## docker-compose.yml walkthrough

### `volumes: - ./output:/app/output`

Bind-mounts the host `./output/` directory into the container at `/app/output`. Files written there during the run are immediately visible on the host. The directory is created by Docker if it does not exist.

### `runtime: runc`

Explicitly selects the standard OCI runtime. Without this, Docker may default to `nvidia-container-runtime` if a GPU driver was previously installed — which fails on machines where the NVIDIA runtime is no longer present. `runc` is always available and is the correct choice for a CPU-only workload.

### Two services

| Service    | Purpose                          | Command                          |
|------------|----------------------------------|----------------------------------|
| `analysis` | Run the pipeline, write outputs  | `python run_analysis.py`         |
| `tests`    | Run the test suite in the image  | `uv run pytest tests/ -v`        |

`tests` uses `uv run` rather than the activated venv because it needs the dev dependency group (pytest), which was excluded from the image's default venv. `uv run` resolves and runs in a temporary overlay that includes dev deps without rebuilding the image.

---

### Document Control

| Version | Date       | Author           | Change          |
|---------|------------|------------------|-----------------|
| 1.0     | 2026-04-20 | Martin Diergardt | Initial version |
