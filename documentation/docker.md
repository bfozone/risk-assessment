# Docker Setup

## What this does

Docker packages the analysis pipeline (Python 3.13, dependencies, data, code) into a self-contained image and runs it in an isolated container. Results are written to `./output/` on the host. You do not need Python or `uv` installed locally — only Docker.

## Prerequisites

- **Docker Desktop** (macOS, Windows) or **Docker Engine** (Linux)
- ~2 GB free disk space for the image
- Run all commands from the **repo root**

## Running the analysis

### First build

```bash
docker compose up --build
```

Expect 5–10 minutes the first time (pulling the base image, resolving ~100 packages). Subsequent builds are faster thanks to layer caching. When the pipeline finishes, output files appear in `./output/` on the host.

Stop with `Ctrl-C`. For a full shutdown including network cleanup: `docker compose down`.

### Subsequent runs

```bash
docker compose up          # reuses the cached image
```

Drop `--build` unless `pyproject.toml`, `uv.lock`, or source code has changed. If only `data/` changed, Docker rebuilds just the data layer — still fast.

### Running the tests

```bash
docker compose run --rm tests
```

The `--rm` flag removes the container after the tests finish (unlike `up`, which cleans up automatically). The first test run installs dev dependencies into the image's venv; subsequent runs reuse them.

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| Build fails during `uv sync` | Check network; `uv.lock` and `pyproject.toml` must be consistent. Re-run with `--no-cache` if the cache is suspect: `docker compose build --no-cache` |
| Code changes not reflected | Rebuild: `docker compose up --build` |
| Out of disk space | `docker system prune -a` (removes unused images and build cache) |
| Apple Silicon build slow | Expected — base image is multi-arch but package wheels may build from source. First build is slow; subsequent builds cache |
| View logs after run | `docker compose logs analysis` |

## What's in the image

`.dockerignore` excludes development artefacts from the build context:

- `notebooks/`, `README.md`, `REPORT.md`, `Makefile`, `.github/`
- caches (`__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`)
- local environments (`.venv/`, `venv/`, `env/`)
- `output/`, `internal/`, VCS metadata

**Notebooks are not included in the image.** They are development-only artefacts meant to run on the host. The container runs the scripted pipeline (`run_analysis.py`), not the notebooks.

---

## Technical appendix — Dockerfile design

### Base image — `python:3.13-slim`

Debian-based image with the CPython interpreter and nothing else. Standard choice for projects without compiled C extensions that require a build toolchain at runtime. `alpine` would be smaller, but its musl libc causes subtle incompatibilities with glibc wheels (numpy, pandas, scipy all ship glibc wheels) — in practice these libraries sometimes fail to install on Alpine. The size saving is not worth the friction.

### uv installation

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:0.4.25 /uv /uvx /bin/
```

uv is copied as a static binary from the official image — no `apt-get` or `pip install uv`. The version tag is pinned for reproducibility; update deliberately when upgrading uv. Using `:latest` would make builds non-deterministic.

### Layer ordering

```dockerfile
# Layer 1 — dependencies (lockfile-stable)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Layer 2 — project source + tests (changes on code edits)
COPY src/ ./src/
COPY tests/ ./tests/
COPY run_analysis.py setup_check.py ./
RUN uv sync --frozen --no-dev

# Layer 3 — data (changes most frequently)
COPY data/ ./data/
```

Docker invalidates all layers below a changed `COPY`. Splitting slow operations (dependency resolution) from fast ones (project install, data copy) means:

- editing source → only Layer 2+ re-run; dependencies are cached
- updating data → only Layer 3 re-runs; both dependency layers are cached
- changing `pyproject.toml` / `uv.lock` → full rebuild (correct, since deps changed)

`--no-install-project` on Layer 1 installs third-party packages only and defers the project itself until its source is available in Layer 2.

### Key flags

- **`--frozen`** — uv must use `uv.lock` exactly as written; no updates. Deterministic builds across machines and CI.
- **`--no-dev`** — excludes the `[dependency-groups] dev` packages (jupyterlab, ruff, pytest, debugpy, ~30 packages). Production image contains only runtime dependencies.

### Virtual environment activation

```dockerfile
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "run_analysis.py", "--output-dir", "/app/output"]
```

`uv sync` creates `.venv` inside `/app`. Setting `VIRTUAL_ENV` and prepending its `bin/` to `PATH` activates it for subsequent commands and the final `CMD` without going through `uv run`. Invoking `python` directly from the activated venv avoids any runtime resolution step on container start.

### `mkdir output`

Creates `/app/output` inside the image for standalone runs. In the compose workflow this directory is hidden by the bind mount from `./output`, so the `mkdir` only matters if the image is run without compose.

### No non-root user

A dedicated non-root user is standard hardening for production images. It is not configured here because the container's only purpose is writing to a bind-mounted host directory; adding a non-root user would require matching UIDs between container and host (or `chmod`/`chown` steps) without a meaningful security benefit for a local analysis workload.

---

## Technical appendix — Compose design

### `volumes: - ./output:/app/output`

Bind-mounts the host `./output/` directory into the container. Files written there during the run are immediately visible on the host. Docker creates the directory if it does not exist.

### `runtime: runc`

Pins the OCI runtime explicitly. Some ML workstations configure `nvidia-container-runtime` as the default in `/etc/docker/daemon.json`; pinning `runc` ensures this compose file behaves identically regardless of the host's Docker daemon configuration. On a stock Docker install this line is a no-op; safe to keep.

### Two services, one image

Both services build from the same Dockerfile. The `analysis` service uses the Dockerfile's default `CMD`. The `tests` service overrides `command:` to run pytest:

| Service    | Command                               | Notes                                        |
|------------|-------------------------------------- |----------------------------------------------|
| `analysis` | `python run_analysis.py` (from `CMD`) | Production runtime, no dev dependencies      |
| `tests`    | `uv run pytest tests/ -v`             | Requires pytest from the dev group           |

`uv run pytest` detects that pytest is not installed in the image's venv, resolves the dev dependency group on the fly, and installs those packages into the venv before running. The first test run performs this sync (~30 packages); subsequent runs reuse the populated venv, so they are faster.

---

### Document Control

| Version | Date       | Author           | Tooling     | Change          |
|---------|------------|------------------|-------------|-----------------|
| 1.0     | 2026-04-20 | Martin Diergardt | Claude Code | Initial version |
