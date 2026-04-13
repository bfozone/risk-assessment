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
    raise NotImplementedError
