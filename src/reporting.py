"""
Output generation for the risk analysis pipeline.

All functions write to the provided output directory. Plots are saved
as PNG files; structured data as JSON or CSV.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter


def _to_json_serializable(obj: object) -> object:
    """Recursively convert numpy/pandas types to JSON-serializable Python types."""
    if isinstance(obj, dict):
        return {k: _to_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_serializable(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return str(obj.date())
    return obj


def write_metrics_json(metrics: dict, output_dir: Path) -> Path:
    """
    Write risk metrics (VaR/CVaR, component VaR) to a JSON file.

    Args:
        metrics: Dictionary of computed risk metrics.
        output_dir: Directory to write the file in.

    Returns:
        Path to the written file.

    """
    path = output_dir / "risk_metrics.json"
    path.write_text(json.dumps(_to_json_serializable(metrics), indent=2))
    return path


def write_backtest_json(backtest_results: dict, output_dir: Path) -> Path:
    """Write backtest results (breach dates, counts, Kupiec test) to JSON."""
    serializable = {
        k: v
        for k, v in backtest_results.items()
        if k not in ("var_series", "actual_returns")
    }
    path = output_dir / "backtest.json"
    path.write_text(json.dumps(_to_json_serializable(serializable), indent=2))
    return path


def write_scenarios_csv(
    scenario_results: pd.DataFrame,
    output_dir: Path,
) -> Path:
    """Write stress scenario results to a CSV file."""
    path = output_dir / "scenarios.csv"
    scenario_results.to_csv(path, index=False)
    return path


def plot_backtest(
    var_series: pd.Series,
    actual_returns: pd.Series,
    breach_dates: list,
    output_dir: Path,
) -> Path:
    """
    Create and save the VaR backtest visualization as a PNG.

    The plot shows:
      - Daily portfolio returns (bars)
      - Rolling VaR threshold (line)
      - Breach points (markers)

    """
    fig, ax = plt.subplots(figsize=(14, 5))

    colors = ["tab:red" if r < 0 else "tab:blue" for r in actual_returns]
    ax.bar(
        actual_returns.index,
        actual_returns.to_numpy(),
        color=colors,
        alpha=0.6,
        label="Daily return",
    )
    ax.plot(
        var_series.index,
        -var_series.to_numpy(),
        color="black",
        linewidth=1.2,
        label="VaR threshold",
    )

    if breach_dates:
        breach_returns = actual_returns.loc[breach_dates]
        ax.scatter(
            breach_returns.index,
            breach_returns.to_numpy(),
            color="red",
            zorder=5,
            label="Breach",
        )

    ax.axhline(0, color="grey", linewidth=0.5)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.1%}"))
    ax.set_title("Rolling VaR Backtest")
    ax.set_xlabel("Date")
    ax.set_ylabel("Return")
    ax.legend()
    plt.tight_layout()

    path = output_dir / "backtest.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def plot_correlation_heatmap(returns: pd.DataFrame, output_dir: Path) -> Path:
    """Create and save a correlation heatmap of instrument returns as a PNG."""
    corr = returns.corr()

    fig, ax = plt.subplots(figsize=(14, 11))
    im = ax.imshow(corr.values, vmin=-1, vmax=1, cmap="RdBu_r")
    plt.colorbar(im, ax=ax, fraction=0.03)

    ticks = range(len(corr))
    ax.set_xticks(list(ticks))
    ax.set_yticks(list(ticks))
    ax.set_xticklabels(corr.columns.tolist(), rotation=90, fontsize=8)
    ax.set_yticklabels(corr.index.tolist(), fontsize=8)
    ax.set_title("Return Correlation Matrix")
    plt.tight_layout()

    path = output_dir / "correlation_heatmap.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def write_summary_text(
    metrics: dict,
    backtest_results: dict,
    scenario_results: pd.DataFrame,
    output_dir: Path,
) -> Path:
    """Write a human-readable text summary of the analysis."""
    kupiec = backtest_results.get("kupiec", {})
    lines = [
        "BAM Risk Assessment — Summary",
        "=" * 40,
        "",
        "Risk Metrics",
        "-" * 20,
    ]

    for key, val in metrics.items():
        if isinstance(val, float):
            lines.append(f"  {key}: {val:.4%}")
        elif isinstance(val, dict):
            lines.append(f"  {key}:")
            for k2, v2 in val.items():
                lines.append(
                    f"    {k2}: {v2:.4%}"
                    if isinstance(v2, float)
                    else f"    {k2}: {v2}"
                )
        else:
            lines.append(f"  {key}: {val}")

    lines += [
        "",
        "Backtest",
        "-" * 20,
        f"  Observations:      {backtest_results.get('n_observations')}",
        f"  Expected breaches: {backtest_results.get('expected_breaches'):.1f}",
        f"  Observed breaches: {backtest_results.get('n_breaches')}",
        f"  Kupiec p-value:    {kupiec.get('p_value', float('nan')):.4f}",
        f"  Kupiec reject H0:  {kupiec.get('reject_h0')}",
        "",
        "Stress Scenarios",
        "-" * 20,
    ]

    for _, row in scenario_results.iterrows():
        lines.append(
            f"  {row['scenario_name']}: return={row['portfolio_return']:.2%}, "
            f"P&L=CHF {row['pnl_chf']:,.0f}"
        )

    path = output_dir / "summary.txt"
    path.write_text("\n".join(lines) + "\n")
    return path
