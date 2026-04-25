#!/usr/bin/env python3

# Orchestrator file for the app

import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

# --- Project imports under folder src, incl. all the functions in the .py files-------------------------------------------------------

from src.data_loader import (
    clean_prices,
    load_instruments,
    load_positions,
    load_prices,
    load_scenarios,
)
from src.returns import (
    build_returns_wide,
    compute_portfolio_returns,
)
from src.risk_metrics import (
    compute_component_var,
    compute_cvar_historical,
    compute_cvar_parametric,
    compute_var_historical,
    compute_var_parametric,
    compute_var_ewma,
)
from src.backtest import run_rolling_backtest, run_rolling_backtest_ewma
from src.stress import apply_scenarios
from src.reporting import (
    plot_backtest,
    plot_correlation_heatmap,
    plot_scenarios,
    write_backtest_json,
    write_metrics_json,
    write_scenarios_csv,
    write_summary_text,
)


# --- Path configuration ----------------------------------------------------
# Rooting paths at __file__ means this script works from any working directory — inside the container (WORKDIR /app), in a local venv, or
# invoked from an absolute path.
# It is a safer way instead of using strings. Plus it does not depend on the current working directory


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"

DB_PATH = DATA_DIR / "reference.duckdb"
PRICES_PATH = DATA_DIR / "prices.parquet"
SCENARIOS_PATH = DATA_DIR / "scenarios.parquet"


# --- Pipeline parameters ---------------------------------------------------
# I kept it as constants so that they can be easily changed in prod.
BACKTEST_WINDOW = 60          
BACKTEST_CONFIDENCE = 0.99    
METRIC_CONFIDENCES = (0.95, 0.99)


# --- Logging setup ---------------------------------------------------------
# Simple stdout logging. PYTHONUNBUFFERED=1 in the Dockerfile ensures these
# appear live in `docker logs` / `docker compose up` output.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("risk_pipeline")


# --- Helper: adapt backtest output to reporting contract -------------------
# run_rolling_backtest currently returns {"backtest_df": ..., "summary": ...}
# but reporting.py expects a flat dict. This adapter is the single place
# that bridges the two.

def _adapt_backtest_for_reporting(backtest_raw: dict) -> dict:
    """Flatten the backtest output into the shape reporting.py expects."""
    df = backtest_raw["backtest_df"].copy()
    summary = backtest_raw["summary"]

    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()

    var_series = df["var_threshold"]       # negative values, e.g. -0.025
    actual_returns = df["realized_return"]

    return {
        "model": summary.get("model", "unknown"),
        "n_obs": summary["n_obs"],
        "n_breaches": summary["n_breaches"],
        "expected_breaches": summary["expected_breaches"],
        "breach_dates": summary["breach_dates"],
        "kupiec_test": summary["kupiec_test"],
        "var_series": var_series,
        "actual_returns": actual_returns,
    }


# --- Main pipeline ---------------------------------------------------------

# I configured the logging so that it is strctured and clear. Ideal for Docker.
# This is the main orchestration function

def main() -> int:
    #banner creation
    log.info("=" * 60)
    log.info("Investment Risk Analysis Pipeline")
    log.info("=" * 60)
    log.info("Root:       %s", ROOT)
    log.info("Data dir:   %s", DATA_DIR)
    log.info("Output dir: %s", OUTPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    #Streamlit

    completion_marker = OUTPUT_DIR / "_RUN_COMPLETE"
    if completion_marker.exists():
       completion_marker.unlink()

    # -- Loading data step --------------------------------------------------

    # Logs the first pipeline step
    log.info("[1/6] Loading reference data, positions, prices and scenarios")

    instruments = load_instruments(str(DB_PATH))
    positions = load_positions(str(DB_PATH))
    prices_raw = load_prices(str(PRICES_PATH))
    scenarios = load_scenarios(str(SCENARIOS_PATH))

    # This is a sort of control to help me seeing what the pipeline steps are doing.

    log.info("Instruments: %d", len(instruments))
    log.info("Positions:   %d (NAV Fund = %.0f CHF)",
             len(positions), positions["market_value_chf"].sum())
    log.info("Prices raw:  %d rows", len(prices_raw))
    log.info("Scenarios:   %d shock rows across %d scenarios",
             len(scenarios), scenarios["scenario_id"].nunique())

    # Weights should sum to roughly 1
    weight_sum = positions["weight"].sum()
    if abs(weight_sum - 1.0) > 0.01:
        log.warning("Portfolio weights are summing to %.4f, not 1.0", weight_sum)

    # -- Data Cleaning step-----------------------------

    log.info("[2/6] Cleaning prices and building return matrix")

    # Again these logs help me spotting mistakes and controlling the flow

    prices_clean = clean_prices(prices_raw)

    log.info("Prices ex-post cleaning: %d rows (from %d)",
             len(prices_clean), len(prices_raw))

    returns_wide = build_returns_wide(prices_clean)

    log.info("Returns matrix: %d days x %d instruments",
             *returns_wide.shape)

    portfolio_returns = compute_portfolio_returns(returns_wide, positions)

    log.info("Portfolio return series: %d days, mean=%.4f%%, vol=%.4f%%",
             len(portfolio_returns),
             portfolio_returns.mean() * 100,
             portfolio_returns.std() * 100)

    # -- Configuration of Risk metrics step -----------------------------------------------

    log.info("[3/6] Computing risk metrics (VaR/CVaR (ES), Component VaR)")

    metrics = {
        "historical": {},
        "parametric": {},
        "ewma": {},
        "component_var_by_sub_class": [],
        "portfolio_stats": {
            "n_observations": int(len(portfolio_returns)),
            "mean_return": float(portfolio_returns.mean()),
            "volatility": float(portfolio_returns.std()),
            "nav_chf": float(positions["market_value_chf"].sum()),
        },
    }

    # Looping over the various risk metrics functions with the two confidence intervals

    for conf in METRIC_CONFIDENCES:
        tag = f"{int(conf * 100)}"
        metrics["historical"][f"var_{tag}"] = compute_var_historical(
            portfolio_returns, confidence=conf
        )
        metrics["historical"][f"cvar_{tag}"] = compute_cvar_historical(
            portfolio_returns, confidence=conf
        )
        metrics["parametric"][f"var_{tag}"] = compute_var_parametric(
            portfolio_returns, confidence=conf
        )
        metrics["parametric"][f"cvar_{tag}"] = compute_cvar_parametric(
            portfolio_returns, confidence=conf
        )
        metrics["ewma"][f"var_{tag}"] = compute_var_ewma(
        portfolio_returns, confidence=conf
        )

    log.info("      Historical VaR 95%%: %.4f%% | VaR 99%%: %.4f%%",
             metrics["historical"]["var_95"] * 100,
             metrics["historical"]["var_99"] * 100)
    log.info("      Parametric VaR 95%%: %.4f%% | VaR 99%%: %.4f%%",
             metrics["parametric"]["var_95"] * 100,
             metrics["parametric"]["var_99"] * 100)
    log.info("      EWMA VaR 95%%: %.4f%% | VaR 99%%: %.4f%%",
             metrics["ewma"]["var_95"] * 100,
             metrics["ewma"]["var_99"] * 100)

    component_var_df = compute_component_var(
        returns_wide, positions, confidence=0.95
    )
    metrics["component_var_by_sub_class"] = component_var_df.to_dict(
        orient="records"
    )
    log.info("Component VaR computed across %d sub-classes",
             len(component_var_df))

    # -- Rolling VaR backtest step ---------------------------------------

    log.info("[4/6] Running rolling VaR backtest (window=%d, conf=%.2f)",
            BACKTEST_WINDOW, BACKTEST_CONFIDENCE)

    # --- Historical VaR backtest
    backtest_hist = run_rolling_backtest(
        port_returns=portfolio_returns,
        window=BACKTEST_WINDOW,
        confidence=BACKTEST_CONFIDENCE,
    )

    # --- EWMA VaR backtest
    backtest_ewma = run_rolling_backtest_ewma(
        port_returns=portfolio_returns,
        window=BACKTEST_WINDOW,
        confidence=BACKTEST_CONFIDENCE, 
    )

    # --- Extract summaries
    hist = backtest_hist["summary"]
    ewma = backtest_ewma["summary"]

    # --- Comparison logging (CRITICAL)
    log.info(" Backtest comparison (%.0f%% VaR):", BACKTEST_CONFIDENCE * 100)

    log.info(
        "      HISTORICAL → Observations: %d | Breaches: %d | Expected: %.2f",
        hist["n_obs"],
        hist["n_breaches"],
        hist["expected_breaches"],
    )
    log.info(
        "      HISTORICAL → Kupiec p-value: %.4f | Reject H0 at 95%%: %s",
        hist["kupiec_test"]["p_value"],
        hist["kupiec_test"]["reject_95pct"],
    )

    log.info(
        "      EWMA → Observations: %d | Breaches: %d | Expected: %.2f",
        ewma["n_obs"],
        ewma["n_breaches"],
        ewma["expected_breaches"],
    )
    log.info(
        "      EWMA → Kupiec p-value: %.4f | Reject H0 at 95%%: %s",
        ewma["kupiec_test"]["p_value"],
        ewma["kupiec_test"]["reject_95pct"],
    )

    # --- Select final model for reporting (recommended: EWMA)
    backtest_raw = backtest_ewma
    backtest_results = _adapt_backtest_for_reporting(backtest_raw)

    log.info("Using EWMA VaR backtest for exported reporting outputs")
    
    # -- Stress scenarios step -------------------------------------------

    log.info("[5/6] Applying stress scenarios")

    scenario_results = apply_scenarios(positions, scenarios)
    log.info("Processed %d scenarios", len(scenario_results))
    worst = scenario_results.iloc[0]  # already sorted ascending by P&L
    log.info("Worst: %s | P&L = %.0f CHF (%.2f%%)",
             worst["scenario_name"],
             worst["portfolio_pnl_chf"],
             worst["portfolio_return"] * 100)

    # -- Write outputs step ----------------------------------------------

    log.info("[6/6] Writing outputs to %s", OUTPUT_DIR)

    written = []

    written.append(write_metrics_json(metrics, OUTPUT_DIR))
  

    backtest_for_json = {
        k: v for k, v in backtest_results.items()
        if k not in ("var_series", "actual_returns")
    }
    written.append(write_backtest_json(backtest_for_json, OUTPUT_DIR))
    written.append(write_scenarios_csv(scenario_results, OUTPUT_DIR))

    try:
        written.append(plot_scenarios(scenario_results, OUTPUT_DIR))
    except Exception as e:
       log.warning("      Scenario plot failed: %s", e)

    try:
        written.append(
            plot_backtest(
                var_series=backtest_results["var_series"],
                actual_returns=backtest_results["actual_returns"],
                breach_dates=backtest_results["breach_dates"],
                output_dir=OUTPUT_DIR,
            )
        )
    except Exception as e:
        log.warning("Backtest plot failed: %s", e)

    try:
        written.append(plot_correlation_heatmap(returns_wide, OUTPUT_DIR))
    except Exception as e:
        log.warning("Correlation heatmap failed: %s", e)

    try:
        written.append(
            write_summary_text(
                metrics=metrics,
                backtest_results=backtest_for_json,
                scenario_results=scenario_results,
                output_dir=OUTPUT_DIR,
            )
        )
    except Exception as e:
        log.warning("Summary text failed: %s", e)

    log.info("Wrote %d files:", len(written))
    for p in written:
        log.info("        - %s", p.name)

    completion_marker.write_text(
         f"completed_at={datetime.now(timezone.utc).isoformat()}",
         encoding="utf-8",
    )
    log.info("        - %s", completion_marker.name)

    log.info("=" * 60)
    log.info("Pipeline has been completed!!!!")
    log.info("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception:
        log.exception("Pipeline failed with an exception - Please investigate")
        exit_code = 1
    sys.exit(exit_code)