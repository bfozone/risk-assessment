#!/usr/bin/env python3
"""
Quick environment check for the risk assessment.

Verifies:
  - All required Python packages can be imported
  - Required data files exist
  - Matplotlib can render and save a small PNG (catches missing display
  backends)
  - DuckDB can open the reference database and list tables
"""

import sys
from pathlib import Path


def check():
    errors = []

    # 1. Imports
    for pkg in ["numpy", "pandas", "duckdb", "pyarrow", "scipy", "matplotlib"]:
        try:
            __import__(pkg)
        except ImportError:
            errors.append(f"Missing package: {pkg}")

    # 2. Data files
    for f in [
        "data/reference.duckdb",
        "data/prices.parquet",
        "data/scenarios.parquet",
    ]:
        if not Path(f).exists():
            errors.append(f"Missing data file: {f}")

    # 3. Matplotlib smoke test (use Agg backend so this works in headless envs)
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        tmp_png = Path("/tmp/_setup_check.png")
        fig.savefig(tmp_png)
        plt.close(fig)
        if not tmp_png.exists() or tmp_png.stat().st_size == 0:
            errors.append("matplotlib could not write a PNG")
        tmp_png.unlink(missing_ok=True)
    except Exception as e:
        errors.append(f"matplotlib smoke test failed: {e}")

    # 4. DuckDB smoke test
    try:
        import duckdb

        con = duckdb.connect("data/reference.duckdb", read_only=True)
        tables = [r[0] for r in con.sql("SHOW TABLES").fetchall()]
        con.close()
        expected = {"instruments", "positions_history", "portfolio_meta"}
        missing = expected - set(tables)
        if missing:
            errors.append(f"DuckDB missing tables: {sorted(missing)}")
    except Exception as e:
        errors.append(f"DuckDB smoke test failed: {e}")

    if errors:
        print("SETUP ISSUES FOUND:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("All checks passed. You are ready to start the assessment.")
        sys.exit(0)


if __name__ == "__main__":
    check()
