"""Entry point for the risk analysis pipeline.

HOW TO RUN:
  Locally:  python run_analysis.py
  Docker:   docker compose up --build

WHAT THIS DOES (in order):
  1. Load all data (instruments, positions, prices, scenarios)
  2. Clean prices
  3. Compute portfolio returns
  4. Compute risk metrics (VaR, CVaR, component VaR)
  5. Run rolling backtest
  6. Apply stress scenarios
  7. Write all outputs to ./output/

"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.data_loader import (
    load_instruments,
    load_positions,
    load_prices,
    clean_prices,
    load_scenarios,
)
from src.risk_metrics import (
    compute_var_historical,
    compute_cvar_historical,
    compute_var_parametric,
    compute_cvar_parametric,
    compute_var_ewma,
    compute_cvar_ewma,
    compute_component_var,
)
from src.backtest import run_rolling_backtest
from src.stress import apply_scenarios
from src.reporting import (
    write_metrics_json,
    write_backtest_json,
    write_scenarios_csv,
    plot_backtest,
    plot_correlation_heatmap,
    write_summary_text,
)

# Where output files land (mounted as a Docker volume in docker-compose.yml)
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)



def compute_returns(
    prices_clean: pd.DataFrame,
    positions: pd.DataFrame,
) -> tuple[pd.Series, pd.DataFrame]:
    """Compute daily portfolio returns and per-instrument returns.

    STEPS:
      1. Pivot prices from long format → wide format
            long:  date | instrument_id | price
            wide:  date | UBSG | NESN | ... (one column per instrument)
      2. Compute log returns: ln(P_t / P_{t-1}).
         .shift(1) moves each column down by one row (yesterday's prices).
         np.log() applied element-wise.
         .dropna() removes the first row (NaN because no previous day).
      3. Align weights with columns (some instruments may have no prices).
      4. Portfolio return = weighted sum across instruments per day.

    Returns
    -------
    port_returns       : pd.Series indexed by date
    instrument_returns : pd.DataFrame (dates × instruments)
    """
    # Step 1: pivot to wide format
    prices_wide = prices_clean.pivot(
        index="date", columns="instrument_id", values="price"
    ).sort_index()

    # Step 2: log returns  (shape: dates × instruments, first row removed)
    instrument_returns = np.log(prices_wide / prices_wide.shift(1)).dropna()

    # Step 3: align weights to columns
    # reindex ensures the weight vector matches the column order of instrument_returns
    weights = (
        positions
        .set_index("instrument_id")["weight"]
        .reindex(instrument_returns.columns)
        .fillna(0.0)
    )
    # Normalize weights in case they don't sum exactly to 1 after reindex
    weights = weights / weights.sum()

    # Step 4: portfolio return = dot product (weights · returns) per day
    port_returns = instrument_returns @ weights

    return port_returns, instrument_returns



def main() -> None:
    print("\n── Step 1: Loading data ──────────────────────────────────")
    instruments = load_instruments()
    positions = load_positions()
    raw_prices = load_prices()
    prices = clean_prices(raw_prices)
    scenarios = load_scenarios()

    print(f"  Instruments:  {len(instruments)} rows")
    print(f"  Positions:    {len(positions)} rows, weights sum = {positions['weight'].sum():.4f}")
    print(f"  Raw prices:   {len(raw_prices)} rows ({raw_prices['price'].isna().sum()} NaNs)")
    print(f"  Clean prices: {len(prices)} rows ({prices['price'].isna().sum()} NaNs)")
    print(f"  Scenarios:    {len(scenarios)} rows, {scenarios['scenario_id'].nunique()} scenarios")

    print("\n── Step 2: Computing returns ─────────────────────────────")
    port_returns, instrument_returns = compute_returns(prices, positions)
    print(f"  Portfolio returns: {len(port_returns)} days, "
          f"mean={port_returns.mean():.4f}, std={port_returns.std():.4f}")

    print("\n── Step 3: Computing risk metrics ───────────────────────")
    # Covariance matrix for component VaR
    cov_matrix = instrument_returns.cov().values

    # Weights aligned to the same column order as instrument_returns
    weights_arr = (
        positions
        .set_index("instrument_id")["weight"]
        .reindex(instrument_returns.columns)
        .fillna(0.0)
        .values
    )

    # Component VaR (array, one value per instrument)
    comp_var_arr = compute_component_var(weights_arr, cov_matrix, confidence=0.99)

    # Group component VaR by sub_class
    sub_classes = (
        positions
        .set_index("instrument_id")["sub_class"]
        .reindex(instrument_returns.columns)
        .fillna("OTHER")
    )
    comp_var_series = pd.Series(comp_var_arr, index=instrument_returns.columns)
    comp_var_by_subclass = (
        comp_var_series
        .groupby(sub_classes.values)
        .sum()
        .to_dict()
    )

    metrics = {
        "var_historical_95":  compute_var_historical(port_returns, 0.95),
        "var_historical_99":  compute_var_historical(port_returns, 0.99),
        "cvar_historical_95": compute_cvar_historical(port_returns, 0.95),
        "cvar_historical_99": compute_cvar_historical(port_returns, 0.99),
        "var_parametric_95":  compute_var_parametric(port_returns, 0.95),
        "var_parametric_99":  compute_var_parametric(port_returns, 0.99),
        "cvar_parametric_95": compute_cvar_parametric(port_returns, 0.95),
        "cvar_parametric_99": compute_cvar_parametric(port_returns, 0.99),
        # EWMA VaR — decay 0.99 (slow fade, long memory)
        "var_ewma_99_decay098":  compute_var_ewma(port_returns, 0.99, decay=0.98),
        "cvar_ewma_99_decay098": compute_cvar_ewma(port_returns, 0.99, decay=0.98),
        # EWMA VaR at 95% confidence as well, for completeness
        "var_ewma_95_decay098":  compute_var_ewma(port_returns, 0.95, decay=0.98),
        "cvar_ewma_95_decay098": compute_cvar_ewma(port_returns, 0.95, decay=0.98),
        "component_var_by_subclass": comp_var_by_subclass,
    }

    for key, val in metrics.items():
        if key != "component_var_by_subclass":
            print(f"  {key:<30s}: {val:.4f}")
    print("  component_var_by_subclass:", comp_var_by_subclass)

    print("\n── Step 4: Running backtest ──────────────────────────────")
    backtest_results = run_rolling_backtest(port_returns, window=60, confidence=0.99)
    print(f"  Observations:     {backtest_results['n_observations']}")
    print(f"  Expected breaches:{backtest_results['expected_breaches']:.1f}")
    print(f"  Actual breaches:  {backtest_results['n_breaches']}")
    print(f"  Kupiec p-value:   {backtest_results['kupiec']['p_value']:.4f}")
    print(f"  Kupiec reject H0: {backtest_results['kupiec']['reject_h0']}")

    print("\n── Step 5: Applying stress scenarios ────────────────────")
    scenario_results = apply_scenarios(positions, scenarios)
    for _, row in scenario_results.iterrows():
        print(f"  {row['scenario_name']}: return={row['portfolio_return']:.4f}, "
              f"P&L=CHF {row['pnl_chf']:,.0f}")

    print("\n── Step 6: Writing outputs ───────────────────────────────")
    write_metrics_json(metrics, OUTPUT_DIR)
    write_backtest_json(backtest_results, OUTPUT_DIR)
    write_scenarios_csv(scenario_results, OUTPUT_DIR)
    plot_backtest(
        backtest_results["var_series"],
        backtest_results["actual_returns"],
        backtest_results["breach_dates"],
        OUTPUT_DIR,
    )
    plot_correlation_heatmap(instrument_returns, OUTPUT_DIR)
    write_summary_text(metrics, backtest_results, scenario_results, OUTPUT_DIR)

    print("\n── Done! Output files in ./output/ ──────────────────────\n")


if __name__ == "__main__":
    main()
