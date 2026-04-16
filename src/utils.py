"""Shared utilities for notebooks and scripts."""

import os
import sys
from pathlib import Path


def setup_repo_root() -> Path:
    """
    Ensure the repository root is the working directory and is on sys.path.

    Walks up from this file's location until it finds the repo root
    (identified by the presence of pyproject.toml), then:
      - changes the working directory to that root, and
      - inserts it at the front of sys.path if not already present.

    Returns the resolved repo root as a Path.
    """
    repo_root = None
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            repo_root = current
            break
        current = current.parent

    if repo_root is None:
        raise RuntimeError("Could not locate repo root (no pyproject.toml found)")

    os.chdir(repo_root)
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    return repo_root
