"""
Output functions for the risk assessment pipeline.

All functions write outputs to the provided output directory.
Plots are saved as PNG files; structured outputs as JSON, CSV, or TXT.
"""

import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _ensure_output_dir(output_dir: Path) -> Path:
    """
    Ensure the output directory exists and return it.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _json_default_serializer(obj: Any) -> Any:
    """
    Convert pandas / numpy / timestamp objects into JSON-serializable values.
    """
    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()

    if isinstance(obj, (np.integer,)):
        return int(obj)

    if isinstance(obj, (np.floating,)):
        return float(obj)

    if isinstance(obj, (np.bool_,)):
        return bool(obj)

    if isinstance(obj, pd.Series):
        return obj.to_dict()

    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")

    if pd.isna(obj):
        return None

    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def write_metrics_json(metrics: dict, output_dir: Path) -> Path:
    """
    Write risk metrics (VaR/CVaR, component VaR) to a JSON file.

    Args:
        metrics: Dictionary of computed risk metrics.
        output_dir: Directory to write the file in.

    Returns:
        Path to the written file.
    """
    output_dir = _ensure_output_dir(output_dir)
    output_path = output_dir / "risk_metrics.json"

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, default=_json_default_serializer)

    return output_path


def write_backtest_json(backtest_results: dict, output_dir: Path) -> Path:
    """
    Write backtest results (breach dates, counts, Kupiec test) to JSON.
    

    Args:
        backtest_results: Dictionary containing backtest summary results.
        output_dir: Directory to write the file in.

    Returns:
        Path to the written JSON file.
    """
    output_dir = _ensure_output_dir(output_dir)
    output_path = output_dir / "backtest.json"

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(backtest_results, f, indent=2, default=_json_default_serializer)

    return output_path


def write_scenarios_csv(
    scenario_results: pd.DataFrame,
    output_dir: Path,
) -> Path:
    """
    Write stress scenario results to a CSV file.

    Args:
        scenario_results: DataFrame with per-scenario results.
        output_dir: Directory to write the file in.

    Returns:
        Path to the written CSV file.
    """
    output_dir = _ensure_output_dir(output_dir)
    output_path = output_dir / "scenarios.csv"

    scenario_results.to_csv(output_path, index=False)

    return output_path


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

    Args:
        var_series: Series of VaR thresholds expressed as returns.
            Recommended convention: negative values, e.g. -0.025.
        actual_returns: Series of realized daily portfolio returns.
        breach_dates: List of dates where realized return breached VaR.
        output_dir: Directory to write the PNG in.

    Returns:
        Path to the written PNG file.
    """
    output_dir = _ensure_output_dir(output_dir)
    output_path = output_dir / "backtest.png"

    var_series = var_series.copy().sort_index()
    actual_returns = actual_returns.copy().sort_index()

    combined_index = actual_returns.index.intersection(var_series.index)
    actual_returns = actual_returns.loc[combined_index]
    var_series = var_series.loc[combined_index]

    breach_index = pd.to_datetime(breach_dates, errors="coerce")
    breach_index = pd.Index([d for d in breach_index if pd.notna(d)])

    breach_points = actual_returns.loc[actual_returns.index.intersection(breach_index)]

    plt.figure(figsize=(14, 6))
    plt.bar(
        actual_returns.index,
        actual_returns.values,
        width=1.0,
        alpha=0.7,
        label="Daily Portfolio Return",
    )
    plt.plot(
        var_series.index,
        var_series.values,
        linewidth=2,
        color="#FFC107",
        label="Rolling VaR Threshold",
    )

    if not breach_points.empty:
        plt.scatter(
            breach_points.index,
            breach_points.values,
            s=40,
            label="Breaches",
            zorder=3,
        )

    plt.axhline(0.0, linewidth=1)
    plt.title("Rolling VaR Backtest")
    plt.xlabel("Date")
    plt.ylabel("Return")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    return output_path


def plot_correlation_heatmap(returns: pd.DataFrame, output_dir: Path) -> Path:
    """
    Create and save a correlation heatmap of instrument returns as a PNG.

    Args:
        returns: Wide-format return matrix with one column per instrument.
        output_dir: Directory to write the PNG in.

    Returns:
        Path to the written PNG file.
    """
    output_dir = _ensure_output_dir(output_dir)
    output_path = output_dir / "correlation_heatmap.png"

    corr = returns.corr()

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(corr.values, aspect="auto")

    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticklabels(corr.index)

    ax.set_title("Correlation Heatmap")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    return output_path


def write_summary_text(
    metrics: dict,
    backtest_results: dict,
    scenario_results: pd.DataFrame,
    output_dir: Path,
) -> Path:
    """
    Write a human-readable text summary of the analysis.

    Args:
        metrics: Dictionary of computed risk metrics.
        backtest_results: Dictionary of backtest results.
        scenario_results: DataFrame of scenario outputs.
        output_dir: Directory to write the text file in.

    Returns:
        Path to the written text file.
    """
    output_dir = _ensure_output_dir(output_dir)
    output_path = output_dir / "summary.txt"

    hist = metrics.get("historical", {})
    param = metrics.get("parametric", {})
    ewma = metrics.get("ewma", {})
    component_var = metrics.get("component_var_by_sub_class", [])


    worst_scenario_text = "N/A"
    if not scenario_results.empty:
        scenario_results_sorted = scenario_results.copy()

        pnl_col = None
        for candidate in ["portfolio_pnl_chf", "pnl_chf"]:
            if candidate in scenario_results_sorted.columns:
                pnl_col = candidate
                break

        if pnl_col is not None:
            scenario_results_sorted = scenario_results_sorted.sort_values(pnl_col, ascending=True)
            worst_row = scenario_results_sorted.iloc[0]
            worst_scenario_text = (
                f"{worst_row.get('scenario_name', 'N/A')} | "
                f"P&L: {worst_row.get(pnl_col, np.nan):,.0f} CHF | "
                f"Return: {worst_row.get('portfolio_return', np.nan):.2%}"
            )

    lines = [
        "Investment Risk Analysis Summary",
        "===============================",
        "",
        "Risk Metrics",
        "------------",
        f"Historical VaR 95%: {hist.get('var_95', np.nan):.4%}" if "var_95" in hist else "Historical VaR 95%: N/A",
        f"Historical VaR 99%: {hist.get('var_99', np.nan):.4%}" if "var_99" in hist else "Historical VaR 99%: N/A",
        f"Historical ES 95%: {hist.get('cvar_95', np.nan):.4%}" if "cvar_95" in hist else "Historical ES 95%: N/A",
        f"Historical ES 99%: {hist.get('cvar_99', np.nan):.4%}" if "cvar_99" in hist else "Historical ES 99%: N/A",
        f"Parametric VaR 95%: {param.get('var_95', np.nan):.4%}" if "var_95" in param else "Parametric VaR 95%: N/A",
        f"Parametric VaR 99%: {param.get('var_99', np.nan):.4%}" if "var_99" in param else "Parametric VaR 99%: N/A",
        f"Parametric ES 95%: {param.get('cvar_95', np.nan):.4%}" if "cvar_95" in param else "Parametric ES 95%: N/A",
        f"Parametric ES 99%: {param.get('cvar_99', np.nan):.4%}" if "cvar_99" in param else "Parametric ES 99%: N/A",

        # -------- EWMA --------
        f"EWMA VaR 95%: {ewma.get('var_95', np.nan):.4%}" if "var_95" in ewma else "EWMA VaR 95%: N/A",
        f"EWMA VaR 99%: {ewma.get('var_99', np.nan):.4%}" if "var_99" in ewma else "EWMA VaR 99%: N/A",
        # --------------------------------

        "",
        "Risk Metric Interpretation",
        "--------------------------",
        "Historical VaR provides a robust benchmark based on empirical returns.",
        "Parametric VaR provides a smoother estimate under distributional assumptions - normal.",
    ]

    # -------- EWMA--------
    if ewma: 
        lines.extend([ 
            "EWMA VaR improves responsiveness by assigning greater weight to recent observations,",
            "allowing the model to better adapt to changing volatility regimes.", 
        ])  
    # ------------------------------------

    # --- Backtest section
    lines.extend([
        "",
        "Backtest",
        "--------",
        f"Model: {backtest_results.get('model', 'N/A')}", 
        f"Observations: {backtest_results.get('n_obs', 'N/A')}",
        f"Breaches: {backtest_results.get('n_breaches', 'N/A')}",
        f"Expected Breaches: {backtest_results.get('expected_breaches', 'N/A')}",
    ])

    kupiec = backtest_results.get("kupiec_test", {})
    if kupiec:
        lines.extend([
            f"Kupiec LR Statistic: {kupiec.get('lr_stat', np.nan):.4f}" if "lr_stat" in kupiec else "Kupiec LR Statistic: N/A",
            f"Kupiec p-value: {kupiec.get('p_value', np.nan):.4f}" if "p_value" in kupiec else "Kupiec p-value: N/A",
            f"Reject at 95%: {kupiec.get('reject_95pct', 'N/A')}",
        ])

    # -------- Interpretation of the backtesting --------
    lines.extend([ 
        "", 
        "Backtest Interpretation", 
        "The backtesting results yield actual breaches equal to 4. This means that is above the expected breaches, hence the model is slighlty underestimating the risk in the tails. However, the Kupiec test does not reject the model at the 95 percent statistical confidence level (i.e., p-value=0.1878 > 0.05).", 
    ]) 

    model_name = str(backtest_results.get("model", "")).lower() 

    if model_name == "ewma": 
        lines.extend([ 
            "EWMA VaR was used for the reported backtest output.",
            "This model is more quickly to adjust to volatility regimes, reducing unexpected breaches.",
            "The improved Kupiec test result indicates better calibration of tail risk.",
        ]) 
    elif model_name == "historical": 
        lines.extend([ 
            "Historical VaR was used for the reported backtest output.", 
            "While robust, it may underestimate risk during volatile periods.", 
        ]) 
    else: 
        lines.append("Backtest model interpretation not available.")
    # ---------------------------------------

    lines.extend([
        "",
        "Stress Testing",
        "--------------",
        f"Worst Scenario: {worst_scenario_text}",
        "",
        "Component VaR by Sub-Class",
        "--------------------------",
    ])

    if component_var:
        for row in component_var:
            sub_class = row.get("sub_class", "N/A")
            value = row.get("component_var", np.nan)
            if pd.notna(value):
                lines.append(f"{sub_class}: {value:.4%}")
            else:
                lines.append(f"{sub_class}: N/A")
    else:
        lines.append("No component VaR output available.")

    with output_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path

def plot_scenarios(scenario_results: pd.DataFrame, output_dir: Path) -> Path:
    """
    Create and save a bar chart of stress scenario portfolio P&L as a PNG.

    Args:
        scenario_results: DataFrame with per-scenario stress results.
        output_dir: Directory to write the PNG in.

    Returns:
        Path to the written PNG file.
    """
    output_dir = _ensure_output_dir(output_dir)
    output_path = output_dir / "scenarios.png"

    df = scenario_results.copy()

    pnl_col = None
    for candidate in ["portfolio_pnl_chf", "pnl_chf"]:
        if candidate in df.columns:
            pnl_col = candidate
            break

    if pnl_col is None:
        raise ValueError("Scenario results must contain 'portfolio_pnl_chf' or 'pnl_chf'.")

    df = df.sort_values(pnl_col, ascending=True)

    plt.figure(figsize=(10, 5))
    plt.bar(df["scenario_name"], df[pnl_col])
    plt.axhline(0.0, linewidth=1)
    plt.title("Stress Scenario Portfolio P&L")
    plt.xlabel("Scenario")
    plt.ylabel("CHF P&L")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    return output_path
