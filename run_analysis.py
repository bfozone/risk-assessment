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

import numpy as np
import pandas as pd

from backtest import run_rolling_backtest
from data_loader import clean_prices, load_positions, load_prices, load_scenarios
from reporting import (
    plot_backtest,
    plot_correlation_heatmap,
    write_backtest_json,
    write_metrics_json,
    write_scenarios_csv,
    write_summary_text,
)
from risk_metrics import (
    compute_component_var,
    compute_cvar_historical,
    compute_cvar_parametric,
    compute_var_historical,
    compute_var_parametric,
)
from stress import apply_scenarios


def _build_returns(prices_path: Path, positions: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Load prices, clean them, and return per-instrument and portfolio returns."""
    raw = load_prices(str(prices_path))
    clean = clean_prices(raw)
    prices_wide = clean.pivot(index="date", columns="instrument_id", values="price").sort_index()
    returns = prices_wide.pct_change().dropna(how="all")

    weights = positions.set_index("instrument_id")["weight"]
    common = returns.columns.intersection(weights.index)
    port_returns = returns[common].dot(weights[common])

    return returns[common], port_returns


def _compute_metrics(port_returns: pd.Series, positions: pd.DataFrame, returns: pd.DataFrame) -> dict:
    """Compute VaR/CVaR at 95% and 99%, plus component VaR grouped by sub_class."""
    metrics: dict = {}

    for conf in (0.95, 0.99):
        label = f"{int(conf * 100)}pct"
        metrics[f"var_historical_{label}"] = compute_var_historical(port_returns, conf)
        metrics[f"cvar_historical_{label}"] = compute_cvar_historical(port_returns, conf)
        metrics[f"var_parametric_{label}"] = compute_var_parametric(port_returns, conf)
        metrics[f"cvar_parametric_{label}"] = compute_cvar_parametric(port_returns, conf)

    # Component VaR at 99% by instrument, aggregated to sub_class
    weights_arr = positions.set_index("instrument_id").loc[returns.columns, "weight"].values
    cov = returns.cov().values
    comp_var = compute_component_var(weights_arr, cov, confidence=0.99)

    sub_classes = positions.set_index("instrument_id").loc[returns.columns, "sub_class"]
    comp_df = pd.DataFrame({"component_var": comp_var}, index=returns.columns)
    comp_df["sub_class"] = sub_classes.values
    metrics["component_var_by_subclass"] = (
        comp_df.groupby("sub_class")["component_var"].sum().to_dict()
    )

    return metrics


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

    # 1. Load data
    print("[bam-risk] loading data...")
    db_path = str(args.data_dir / "reference.duckdb")
    positions = load_positions(db_path)
    scenarios = load_scenarios(str(args.data_dir / "scenarios.parquet"))

    returns, port_returns = _build_returns(args.data_dir / "prices.parquet", positions)
    print(f"[bam-risk] returns: {returns.shape}, portfolio series: {len(port_returns)} days")

    # 2. Risk metrics
    print("[bam-risk] computing risk metrics...")
    metrics = _compute_metrics(port_returns, positions, returns)
    metrics_path = write_metrics_json(metrics, args.output_dir)
    print(f"[bam-risk] written {metrics_path.name}")

    # 3. Backtest
    print("[bam-risk] running backtest...")
    backtest = run_rolling_backtest(port_returns, window=60, confidence=0.99)
    backtest_path = write_backtest_json(backtest, args.output_dir)
    print(
        f"[bam-risk] backtest: {backtest['n_breaches']}/{backtest['n_observations']} breaches "
        f"(Kupiec p={backtest['kupiec']['p_value']:.3f}) → {backtest_path.name}"
    )

    # 4. Stress scenarios
    print("[bam-risk] applying stress scenarios...")
    scenario_results = apply_scenarios(positions, scenarios)
    scenarios_path = write_scenarios_csv(scenario_results, args.output_dir)
    print(f"[bam-risk] written {scenarios_path.name}")

    # 5. Charts and summary
    print("[bam-risk] generating charts...")
    bt_chart = plot_backtest(
        backtest["var_series"],
        backtest["actual_returns"],
        backtest["breach_dates"],
        args.output_dir,
    )
    print(f"[bam-risk] written {bt_chart.name}")

    heatmap = plot_correlation_heatmap(returns, args.output_dir)
    print(f"[bam-risk] written {heatmap.name}")

    summary = write_summary_text(metrics, backtest, scenario_results, args.output_dir)
    print(f"[bam-risk] written {summary.name}")

    print("[bam-risk] done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
