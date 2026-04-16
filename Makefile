# =========================================================
# Makefile
# =========================================================
#
# Provides tasks for:
# - Setting up virtual environments
# - Installing dependencies
# - Running the analysis pipeline
# - Running tests
# - Formatting and linting code

# Usage examples:
# - make install    # Setup environment + install dependencies
# - make run        # Run the full risk analysis pipeline
# - make test       # Run unit tests
# - make format     # Format code
# - make check      # Run lint, typecheck, and tests

# =========================================================
# Variables
# =========================================================

VENV          := .venv
VENV_BIN      := $(VENV)/bin
PYTHON        := $(VENV_BIN)/python

PACKAGE_NAME  := bam-risk-assessment
SRC           := src
TESTS         := tests

.DEFAULT_GOAL := help

.PHONY: help install run setup-check notebook notebook-kernel test coverage lint format typecheck check clean

help: ## Show all available commands
	@grep -hE '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS=":.*##"} {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

$(VENV)/.installed: pyproject.toml uv.lock
	uv sync --group dev
	@touch $@

install: $(VENV)/.installed ## Install project (skipped if up to date)

run: $(VENV)/.installed ## Run the full risk analysis pipeline
	uv run python run_analysis.py

setup-check: $(VENV)/.installed ## Run environment smoke test (setup_check.py)
	uv run python setup_check.py

notebook-kernel: $(VENV)/.installed ## Register venv as a Jupyter kernel
	uv run python -m ipykernel install --user --name=$(PACKAGE_NAME) \
	    --display-name "Python $$(uv run python -c 'import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}\")') ($(PACKAGE_NAME))"

notebook: notebook-kernel ## Launch Jupyter Lab
	uv run jupyter lab

# =========================================================
# Testing
# =========================================================

test: $(VENV)/.installed ## Run pytest
	@echo "Running tests..."
	uv run pytest $(TESTS)

coverage: $(VENV)/.installed ## Run tests with coverage report
	uv run pytest --cov $(TESTS)

# =========================================================
# Code Quality
# =========================================================

lint: $(VENV)/.installed ## Run Ruff for linting
	uv run ruff check $(SRC) $(TESTS)

format: $(VENV)/.installed ## Auto-fix lint + format
	uv run ruff check --fix $(SRC) $(TESTS)
	uv run ruff format $(SRC) $(TESTS)

typecheck: $(VENV)/.installed ## Run basedpyright static type checking
	uv run basedpyright $(SRC)

check: lint typecheck test ## Run lint + typecheck + tests

# =========================================================
# Cleaning
# =========================================================

clean: ## Remove caches and virtual environment
	@echo "Cleaning up..."
	rm -rf $(VENV) .pytest_cache .ruff_cache output/*
	find . -type d -name '__pycache__' -exec rm -rf {} +
