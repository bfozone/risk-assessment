"""Stress Testing logic and framework"""


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
    required_positions = {"instrument_id", "market_value_chf"}
    required_scenarios = {"scenario_id", "scenario_name", "instrument_id", "shock_return"}

    missing_positions = required_positions - set(positions.columns)
    missing_scenarios = required_scenarios - set(scenarios.columns)

    if missing_positions:
        raise ValueError(f"Positions missing columns: {sorted(missing_positions)}")
    if missing_scenarios:
        raise ValueError(f"Scenarios missing columns: {sorted(missing_scenarios)}")

    scenarios = scenarios.copy()

    if "description" not in scenarios.columns:
        scenarios["description"] = ""

    nav = positions["market_value_chf"].sum()

    merged = scenarios.merge(
        positions[["instrument_id", "market_value_chf"]],
        on="instrument_id",
        how="left",
    )

    merged["market_value_chf"] = merged["market_value_chf"].fillna(0.0)
    merged["pnl_chf"] = merged["market_value_chf"] * merged["shock_return"]

    scenario_summary = (
        merged.groupby(["scenario_id", "scenario_name"], as_index=False)
        .agg(
            portfolio_pnl_chf=("pnl_chf", "sum"),
            description=("description", "first"),
        )
        .sort_values("portfolio_pnl_chf")
        .reset_index(drop=True)
    )

    scenario_summary["portfolio_return"] = scenario_summary["portfolio_pnl_chf"] / nav

    return scenario_summary