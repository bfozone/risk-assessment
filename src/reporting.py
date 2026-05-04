"""Output generation for the risk analysis pipeline.

All functions write to the provided output directory.
  - Structured data → JSON or CSV
  - Visualisations → PNG (using matplotlib)

IMPORTANT — HEADLESS PLOTTING:
  In a Docker container there is no screen (no GUI).
  matplotlib.use("Agg") switches to a non-interactive backend
  that writes directly to a file instead of opening a window.
  This MUST be called before importing pyplot.

JSON AND NUMPY:
  Python's built-in json module doesn't know how to serialise numpy
  types (np.float64, np.int64, etc.). We fix this with a custom
  NumpyEncoder class that converts them to plain Python types first.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # must come before pyplot import; enables headless rendering
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd



class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy scalar and array types.

    HOW json.JSONEncoder WORKS:
      When json.dumps() encounters a type it doesn't know,
      it calls .default(obj) on the encoder.
      We override that to convert numpy types to native Python types.
    """
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)



def write_metrics_json(metrics: dict, output_dir: Path) -> Path:
    """Write VaR/CVaR and component VaR metrics to JSON.

    Args:
        metrics: Dict produced by run_analysis.py (VaR numbers, component VaR by sub_class).
        output_dir: Directory to write the file in.

    Returns
    -------
    Path to the written file.
    """
    path = output_dir / "risk_metrics.json"
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2, cls=NumpyEncoder)
    print(f"  Wrote {path}")
    return path


def write_backtest_json(backtest_results: dict, output_dir: Path) -> Path:
    """Write backtest results to JSON.

    We extract the serialisable parts of backtest_results.
    (var_series and actual_returns are pandas Series — we skip them here;
    they are used for the plot instead.)

    Returns
    -------
    Path to the written file.
    """
    # Convert dates to ISO strings (JSON doesn't have a date type)
    breach_dates_str = [str(d)[:10] for d in backtest_results["breach_dates"]]

    serialisable = {
        "n_observations": backtest_results["n_observations"],
        "n_breaches": backtest_results["n_breaches"],
        "expected_breaches": backtest_results["expected_breaches"],
        "breach_dates": breach_dates_str,
        "kupiec": backtest_results["kupiec"],
    }

    path = output_dir / "backtest.json"
    with open(path, "w") as f:
        json.dump(serialisable, f, indent=2, cls=NumpyEncoder)
    print(f"  Wrote {path}")
    return path



def write_scenarios_csv(scenario_results: pd.DataFrame, output_dir: Path) -> Path:
    """Write stress scenario results to CSV.

    Returns
    -------
    Path to the written file.
    """
    path = output_dir / "scenarios.csv"
    scenario_results.to_csv(path, index=False)
    print(f"  Wrote {path}")
    return path



def plot_backtest(
    var_series: pd.Series,
    actual_returns: pd.Series,
    breach_dates: list,
    output_dir: Path,
) -> Path:
    """Create and save the VaR backtest visualisation as a PNG.

    THE PLOT SHOWS:
      - Blue bars   : actual daily portfolio returns
      - Red line    : rolling VaR threshold (negated, so it's a loss line)
      - Red dots    : breach dates (days where return < -VaR)

    MATPLOTLIB QUICK INTRO:
      fig, ax = plt.subplots()   creates a Figure (canvas) and Axes (the actual chart area)
      ax.bar(x, y)               draws bars
      ax.plot(x, y)              draws a line
      ax.scatter(x, y)           draws dots
      fig.savefig(path)          saves to disk
      plt.close(fig)             frees memory (important in long-running pipelines)

    Returns
    -------
    Path to the written PNG file.
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    # ── Daily returns as bars ────────────────────────────────────────
    # Colour bars: red when negative (loss day), blue when positive
    bar_colors = ["#c0392b" if r < 0 else "#2980b9" for r in actual_returns]
    ax.bar(actual_returns.index, actual_returns, color=bar_colors, alpha=0.6,
           width=1, label="Daily portfolio return")

    # ── VaR threshold as a negative loss line ────────────────────────
    # var_series is positive (loss magnitude); we negate to show as a floor
    ax.plot(var_series.index, -var_series, color="#e74c3c", linewidth=1.5,
            label="VaR threshold (99%, negated)")

    # ── Breach markers ───────────────────────────────────────────────
    if breach_dates:
        breach_returns = actual_returns.reindex(breach_dates).dropna()
        ax.scatter(breach_returns.index, breach_returns,
                   color="#e74c3c", zorder=5, s=50, marker="x", linewidths=2,
                   label=f"VaR breach ({len(breach_dates)} days)")

    # ── Formatting ───────────────────────────────────────────────────
    ax.axhline(0, color="black", linewidth=0.5, linestyle="--", alpha=0.4)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
    ax.set_xlabel("Date")
    ax.set_ylabel("Daily return")
    ax.set_title("Rolling 99% VaR Backtest — 60-day estimation window", fontsize=13)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()

    path = output_dir / "backtest.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Wrote {path}")
    return path



def plot_correlation_heatmap(returns: pd.DataFrame, output_dir: Path) -> Path:
    """Create and save a correlation heatmap of instrument returns.

    WHAT IS CORRELATION?
      Correlation measures how much two instruments move together.
      +1 = always move together, -1 = always move opposite, 0 = no relationship.
      Bonds and equities often have negative or low correlation —
      that's the benefit of diversification.

    Returns
    -------
    Path to the written PNG file.
    """
    corr = returns.corr()
    n = len(corr.columns)

    fig, ax = plt.subplots(figsize=(max(10, n), max(8, n - 2)))

    # imshow renders a matrix as a coloured grid
    # RdYlGn: red = negative correlation, yellow = zero, green = positive
    im = ax.imshow(corr.values, cmap="RdYlGn", vmin=-1, vmax=1, aspect="auto")

    # Tick labels: instrument names
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(corr.columns, fontsize=8)

    # Colour bar legend
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Pearson correlation", fontsize=9)

    # Annotate each cell with the correlation value
    for i in range(n):
        for j in range(n):
            val = corr.values[i, j]
            color = "white" if abs(val) > 0.7 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=6, color=color)

    ax.set_title("Instrument return correlations (daily log returns)", fontsize=12)
    fig.tight_layout()

    path = output_dir / "correlation_heatmap.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Wrote {path}")
    return path



def write_summary_text(
    metrics: dict,
    backtest_results: dict,
    scenario_results: pd.DataFrame,
    output_dir: Path,
) -> Path:
    """Write a plain-text summary of all results.

    Returns
    -------
    Path to the written .txt file.
    """
    nav = 500_000_000  # CHF 500M fund NAV (from README)

    lines = [
        "=" * 60,
        "  RISK ANALYSIS SUMMARY — CHF 500M Multi-Asset Fund",
        "=" * 60,
        "",
        "VALUE AT RISK & EXPECTED SHORTFALL",
        "-" * 40,
        f"  Historical  VaR 95%:   {metrics['var_historical_95']:.4f}  "
        f"(CHF {metrics['var_historical_95'] * nav:>14,.0f})",
        f"  Historical  VaR 99%:   {metrics['var_historical_99']:.4f}  "
        f"(CHF {metrics['var_historical_99'] * nav:>14,.0f})",
        f"  Historical CVaR 95%:   {metrics['cvar_historical_95']:.4f}  "
        f"(CHF {metrics['cvar_historical_95'] * nav:>14,.0f})",
        f"  Historical CVaR 99%:   {metrics['cvar_historical_99']:.4f}  "
        f"(CHF {metrics['cvar_historical_99'] * nav:>14,.0f})",
        "",
        f"  Parametric  VaR 95%:   {metrics['var_parametric_95']:.4f}  "
        f"(CHF {metrics['var_parametric_95'] * nav:>14,.0f})",
        f"  Parametric  VaR 99%:   {metrics['var_parametric_99']:.4f}  "
        f"(CHF {metrics['var_parametric_99'] * nav:>14,.0f})",
        f"  Parametric CVaR 95%:   {metrics['cvar_parametric_95']:.4f}  "
        f"(CHF {metrics['cvar_parametric_95'] * nav:>14,.0f})",
        f"  Parametric CVaR 99%:   {metrics['cvar_parametric_99']:.4f}  "
        f"(CHF {metrics['cvar_parametric_99'] * nav:>14,.0f})",
        "",
        "EWMA-WEIGHTED VaR & CVaR  (recent returns up-weighted)",
        "-" * 40,
        "  λ=0.99 slow fade (long memory)  |  λ=0.98 fast fade (reacts quickly)",
        "",
        f"  EWMA VaR  95% λ=0.99: {metrics['var_ewma_95_decay099']:.4f}  "
        f"(CHF {metrics['var_ewma_95_decay099'] * nav:>14,.0f})",
        f"  EWMA VaR  99% λ=0.99: {metrics['var_ewma_99_decay099']:.4f}  "
        f"(CHF {metrics['var_ewma_99_decay099'] * nav:>14,.0f})",
        f"  EWMA CVaR 95% λ=0.99: {metrics['cvar_ewma_95_decay099']:.4f}  "
        f"(CHF {metrics['cvar_ewma_95_decay099'] * nav:>14,.0f})",
        f"  EWMA CVaR 99% λ=0.99: {metrics['cvar_ewma_99_decay099']:.4f}  "
        f"(CHF {metrics['cvar_ewma_99_decay099'] * nav:>14,.0f})",
        "",
        f"  EWMA VaR  95% λ=0.98: {metrics['var_ewma_95_decay098']:.4f}  "
        f"(CHF {metrics['var_ewma_95_decay098'] * nav:>14,.0f})",
        f"  EWMA VaR  99% λ=0.98: {metrics['var_ewma_99_decay098']:.4f}  "
        f"(CHF {metrics['var_ewma_99_decay098'] * nav:>14,.0f})",
        f"  EWMA CVaR 95% λ=0.98: {metrics['cvar_ewma_95_decay098']:.4f}  "
        f"(CHF {metrics['cvar_ewma_95_decay098'] * nav:>14,.0f})",
        f"  EWMA CVaR 99% λ=0.98: {metrics['cvar_ewma_99_decay098']:.4f}  "
        f"(CHF {metrics['cvar_ewma_99_decay098'] * nav:>14,.0f})",
        "",
        "COMPONENT VAR BY SUB-CLASS",
        "-" * 40,
    ]

    for sub_class, cvar in sorted(metrics["component_var_by_subclass"].items()):
        lines.append(f"  {sub_class:<20s}: {cvar:+.4f}")

    kupiec = backtest_results["kupiec"]
    reject_str = "REJECTED (model miscalibrated!)" if kupiec["reject_h0"] else "NOT rejected (model OK)"
    lines += [
        "",
        "ROLLING BACKTEST (60-day window, 99% confidence)",
        "-" * 40,
        f"  Backtest period:      {backtest_results['n_observations']} days",
        f"  Expected breaches:    {backtest_results['expected_breaches']:.1f}",
        f"  Observed breaches:    {backtest_results['n_breaches']}",
        f"  Kupiec test statistic:{kupiec['test_statistic']:.4f}",
        f"  Kupiec p-value:       {kupiec['p_value']:.4f}",
        f"  Kupiec H0:            {reject_str}",
        "",
        "STRESS SCENARIOS",
        "-" * 40,
    ]

    for _, row in scenario_results.iterrows():
        ret_pct = row["portfolio_return"] * 100
        lines.append(
            f"  {row['scenario_name']:<30s}: "
            f"return = {ret_pct:+.2f}%,  P&L = CHF {row['pnl_chf']:>15,.0f}"
        )

    lines += ["", "=" * 60]

    content = "\n".join(lines)
    path = output_dir / "summary.txt"
    path.write_text(content)
    print(f"  Wrote {path}")
    return path
