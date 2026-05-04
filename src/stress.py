"""Stress scenario application.

WHAT IS STRESS TESTING?
  We ask: "What would happen to our portfolio if a market crisis hit right now?"
  Each scenario defines a shock_return per instrument.
  E.g., scenario "2008 Financial Crisis":
    UBSG (UBS Group): -35%
    NESN (Nestlé):    -15%
    CHF bonds:         +5%  (flight to safety)

  We then compute:
    portfolio_return = sum over all instruments of (weight × shock_return)
    pnl_chf = sum over all instruments of (market_value_chf × shock_return)

JOINING POSITIONS AND SCENARIOS:
  positions table: instrument_id, weight, market_value_chf, ...
  scenarios table: scenario_id, scenario_name, instrument_id, shock_return

  We join them on instrument_id so each scenario row gets the
  corresponding position weight and market value.
"""

import pandas as pd


def apply_scenarios(
    positions: pd.DataFrame,
    scenarios: pd.DataFrame,
) -> pd.DataFrame:
    """Apply predefined stress scenarios to the portfolio.

    ALGORITHM:
      1. Merge scenarios with positions on instrument_id.
         (left join from scenarios — scenarios drive the iteration)
      2. For each row: weighted_return = weight × shock_return
                       pnl = market_value_chf × shock_return
      3. Group by (scenario_id, scenario_name) and sum both columns.

    WHAT IF AN INSTRUMENT IN THE SCENARIO IS NOT IN OUR PORTFOLIO?
      Its weight and market_value_chf will be NaN after the merge.
      We fill those with 0 — no exposure means no impact.

    Args:
        positions: Portfolio positions with columns including instrument_id,
            weight, market_value_chf, sub_class.
        scenarios: Scenario shocks with columns scenario_id, scenario_name,
            instrument_id, shock_return.

    Returns
    -------
    DataFrame with one row per scenario:
        scenario_id, scenario_name, portfolio_return, pnl_chf
    """
    # ── Merge: attach position weights and values to each shock row ──
    # We only need these columns from positions for the calculation.
    pos_subset = positions[["instrument_id", "weight", "market_value_chf"]]

    merged = scenarios.merge(
        pos_subset,
        on="instrument_id",
        how="left",   # keep all scenario rows, even if instrument not in portfolio
    )

    # Fill missing positions with zero (instrument has no weight in our portfolio)
    merged["weight"] = merged["weight"].fillna(0.0)
    merged["market_value_chf"] = merged["market_value_chf"].fillna(0.0)

    # ── Compute per-row contribution ─────────────────────────────────
    # weighted_return: how much this instrument contributes to portfolio return
    merged["weighted_return"] = merged["weight"] * merged["shock_return"]

    # pnl: how much CHF profit/loss this instrument produces
    merged["pnl"] = merged["market_value_chf"] * merged["shock_return"]

    # ── Aggregate to one row per scenario ────────────────────────────
    result = (
        merged
        .groupby(["scenario_id", "scenario_name"], as_index=False)
        .agg(
            portfolio_return=("weighted_return", "sum"),
            pnl_chf=("pnl", "sum"),
        )
    )

    return result
