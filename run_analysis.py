#!/usr/bin/env python3
"""
Entry point for the BAM Risk Analysis pipeline.

This script orchestrates the full risk analysis:
  1. Load portfolio data from DuckDB and parquet files
  2. Compute risk metrics (VaR/CVaR, component VaR)
  3. Run rolling-window VaR backtest and Kupiec test
  4. Apply predefined stress scenarios
  5. Write results (JSON, CSV, PNG) to the output directory

Usage:
    python run_analysis.py                            # default: data/ -> output/
    python run_analysis.py --output-dir /tmp/results  # custom output directory

The pipeline is designed to run inside a Docker container:
    docker compose up --build
"""

import argparse
import sys
from pathlib import Path

# TODO: import your modules from src/
# from src.data_loader import load_positions, load_prices, clean_prices, load_scenarios
# from src.risk_metrics import ...
# from src.backtest import run_rolling_backtest
# from src.stress import apply_scenarios
# from src.reporting import (
#     write_metrics_json,
#     write_backtest_json,
#     write_scenarios_csv,
#     plot_backtest,
#     plot_correlation_heatmap,
#     write_summary_text,
# )
#
# Note: load_instruments is available if you need instrument metadata
# separately, but load_positions can also JOIN with the instruments
# table to carry sub_class and other fields through the pipeline.


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the BAM risk analysis pipeline.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing reference.duckdb, prices.parquet, scenarios.parquet",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for output files (will be created if it does not exist)",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[bam-risk] data dir:   {args.data_dir}")
    print(f"[bam-risk] output dir: {args.output_dir}")

    # TODO: Implement the pipeline
    #
    # Tip: if you haven't finished a step yet, consider wrapping it
    # so that earlier steps still produce their output files.
    #
    # 1. Load data:
    #      - instruments, positions from DuckDB
    #      - prices from parquet, compute returns
    #      - scenarios from parquet
    #
    # 2. Compute risk metrics:
    #      - Historical VaR/CVaR at 95% and 99%
    #      - Parametric VaR/CVaR at 95% and 99%
    #      - Component VaR by sub_class
    #
    # 3. Run backtest:
    #      - 60-day rolling window, 99% confidence
    #      - Kupiec POF test
    #
    # 4. Stress scenarios:
    #      - Apply the 3 predefined scenarios from scenarios.parquet
    #
    # 5. Write outputs to args.output_dir:
    #      - risk_metrics.json
    #      - backtest.json
    #      - scenarios.csv
    #      - backtest.png
    #      - correlation_heatmap.png
    #      - summary.txt

    print("[bam-risk] TODO: implement the pipeline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
