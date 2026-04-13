"""
Output generation for the risk analysis pipeline.

All functions write to the provided output directory. Plots should be saved
as PNG files; structured data as JSON or CSV.
"""

from pathlib import Path

import pandas as pd


def write_metrics_json(metrics: dict, output_dir: Path) -> Path:
    """
    Write risk metrics (VaR/CVaR, component VaR) to a JSON file.

    Args:
        metrics: Dictionary of computed risk metrics.
        output_dir: Directory to write the file in.

    Returns:
        Path to the written file.

    """
    raise NotImplementedError


def write_backtest_json(backtest_results: dict, output_dir: Path) -> Path:
    """Write backtest results (breach dates, counts, Kupiec test) to JSON."""
    raise NotImplementedError


def write_scenarios_csv(
    scenario_results: pd.DataFrame,
    output_dir: Path,
) -> Path:
    """Write stress scenario results to a CSV file."""
    raise NotImplementedError


def plot_backtest(
    var_series: pd.Series,
    actual_returns: pd.Series,
    breach_dates: list,
    output_dir: Path,
) -> Path:
    """
    Create and save the VaR backtest visualization as a PNG.

    The plot should show:
      - Daily portfolio returns (bars)
      - Rolling VaR threshold (line)
      - Breach points (markers)
    """
    raise NotImplementedError


def plot_correlation_heatmap(returns: pd.DataFrame, output_dir: Path) -> Path:
    """Create and save a correlation heatmap of instrument returns as a PNG."""
    raise NotImplementedError


def write_summary_text(
    metrics: dict,
    backtest_results: dict,
    scenario_results: pd.DataFrame,
    output_dir: Path,
) -> Path:
    """Write a human-readable text summary of the analysis."""
    raise NotImplementedError
