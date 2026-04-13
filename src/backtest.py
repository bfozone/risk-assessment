"""VaR backtesting utilities."""

import pandas as pd


def run_rolling_backtest(
    port_returns: pd.Series,
    window: int = 60,
    confidence: float = 0.99,
) -> dict:
    """
    Run a rolling-window historical VaR backtest.

    For each day after the initial window, estimate VaR from the preceding
    `window` days of returns, then compare against the realized return.

    Args:
        port_returns: Daily portfolio return series (indexed by date).
        window: Estimation window in days.
        confidence: VaR confidence level (e.g., 0.99 for 99%).

    Returns:
        Dictionary with keys:
          - var_series: pd.Series of VaR estimates indexed by date
          - actual_returns: pd.Series of actual returns over the backtest period
          - breach_dates: list of dates where loss exceeded VaR
          - n_breaches: int
          - n_observations: int (length of backtest period)
          - expected_breaches: float
          - kupiec: dict (output of kupiec_pof_test)

    """
    raise NotImplementedError
