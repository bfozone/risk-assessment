"""Stress scenario application."""

import pandas as pd


def apply_scenarios(
    positions: pd.DataFrame,
    scenarios: pd.DataFrame,
) -> pd.DataFrame:
    """
    Apply predefined stress scenarios to the portfolio.

    Args:
        positions: Portfolio positions with columns including instrument_id,
            weight, market_value_chf, sub_class.
        scenarios: Scenario shocks with columns scenario_id, scenario_name,
            instrument_id, shock_return.

    Returns:
        DataFrame summarizing each scenario with columns:
            scenario_id, scenario_name, portfolio_return, pnl_chf

    """
    merged = scenarios.merge(
        positions[["instrument_id", "weight", "market_value_chf"]],
        on="instrument_id",
        how="inner",
    )
    merged = merged.assign(
        weighted_return=merged["weight"] * merged["shock_return"],
        weighted_pnl=merged["market_value_chf"] * merged["shock_return"],
    )
    return merged.groupby(["scenario_id", "scenario_name"], as_index=False).agg(
        portfolio_return=("weighted_return", "sum"),
        pnl_chf=("weighted_pnl", "sum"),
    )


def instrument_stress_attribution(
    positions: pd.DataFrame,
    scenarios: pd.DataFrame,
) -> pd.DataFrame:
    """
    Per-instrument P&L contribution for each scenario.

    Args:
        positions: Portfolio positions (must include sub_class).
        scenarios: Scenario shocks.

    Returns:
        Long-form DataFrame with columns: scenario_id, scenario_name,
        instrument_id, sub_class, shock_return, weighted_return, pnl_chf.

    """
    merged = scenarios.merge(
        positions[["instrument_id", "weight", "market_value_chf", "sub_class"]],
        on="instrument_id",
        how="inner",
    )
    return merged.assign(
        weighted_return=merged["weight"] * merged["shock_return"],
        pnl_chf=merged["market_value_chf"] * merged["shock_return"],
    )[
        [
            "scenario_id",
            "scenario_name",
            "instrument_id",
            "sub_class",
            "shock_return",
            "weighted_return",
            "pnl_chf",
        ]
    ].reset_index(drop=True)


def subclass_stress_breakdown(
    positions: pd.DataFrame,
    scenarios: pd.DataFrame,
) -> pd.DataFrame:
    """
    Scenario P&L aggregated by asset sub_class.

    Useful for identifying which asset class drives each scenario loss
    and for sizing hedges at the sub-class level.

    Returns:
        DataFrame with columns: scenario_id, scenario_name, sub_class,
        weighted_return, pnl_chf.

    """
    attr = instrument_stress_attribution(positions, scenarios)
    return (
        attr.groupby(["scenario_id", "scenario_name", "sub_class"])[["weighted_return", "pnl_chf"]]
        .sum()
        .reset_index()
    )
