"""VaR backtesting utilities."""

import pandas as pd

from risk_metrics import (
    compute_cvar_historical,
    compute_var_ewma,
    compute_var_historical,
    kupiec_pof_test,
)


def run_rolling_backtest(
    port_returns: pd.Series,
    window: int = 60,
    confidence: float = 0.99,
) -> dict:
    """
    Run a rolling-window historical VaR backtest.

    For each day after the initial window, estimate VaR and ES from the
    preceding `window` days of returns, then compare against the realized
    return.

    Args:
        port_returns: Daily portfolio return series (indexed by date).
        window: Estimation window in days.
        confidence: VaR confidence level (e.g., 0.99 for 99%).

    Returns:
        Dictionary with keys:
          - var_series: pd.Series of VaR estimates indexed by date
          - cvar_series: pd.Series of CVaR/ES estimates indexed by date
          - actual_returns: pd.Series of actual returns over the backtest period
          - breach_dates: list of dates where loss exceeded VaR
          - n_breaches: int
          - n_observations: int (length of backtest period)
          - expected_breaches: float
          - kupiec: dict (output of kupiec_pof_test)

    """
    var_values = []
    cvar_values = []
    actual_values = []
    dates = []

    for i in range(window, len(port_returns)):
        window_slice = port_returns.iloc[i - window : i]
        var_values.append(compute_var_historical(window_slice, confidence))
        cvar_values.append(compute_cvar_historical(window_slice, confidence))
        actual_values.append(port_returns.iloc[i])
        dates.append(port_returns.index[i])

    var_series = pd.Series(var_values, index=dates, name="var")
    cvar_series = pd.Series(cvar_values, index=dates, name="cvar")
    actual_returns = pd.Series(actual_values, index=dates, name="returns")

    breach_mask = actual_returns < -var_series
    breach_dates = list(actual_returns.index[breach_mask])
    n_breaches = len(breach_dates)
    n_observations = len(var_series)

    return {
        "var_series": var_series,
        "cvar_series": cvar_series,
        "actual_returns": actual_returns,
        "breach_dates": breach_dates,
        "n_breaches": n_breaches,
        "n_observations": n_observations,
        "expected_breaches": n_observations * (1.0 - confidence),
        "kupiec": kupiec_pof_test(n_observations, n_breaches, confidence),
    }


def run_rolling_backtest_ewma(
    port_returns: pd.Series,
    window: int = 60,
    confidence: float = 0.99,
    lam: float = 0.94,
) -> dict:
    """
    Rolling-window backtest using EWMA-filtered historical simulation VaR.

    Uses Hull-White (1998) filtered HS: each historical return in the
    estimation window is rescaled by the ratio of the current EWMA volatility
    forecast to its EWMA vol at the time.  This reduces regime-lag bias
    relative to flat historical simulation.

    Args:
        port_returns: Daily portfolio return series (indexed by date).
        window: Estimation window in days.
        confidence: VaR confidence level.
        lam: EWMA decay factor (0.94 = RiskMetrics daily standard).

    Returns:
        Same structure as run_rolling_backtest (without cvar_series).

    """
    var_values = []
    actual_values = []
    dates = []

    for i in range(window, len(port_returns)):
        window_slice = port_returns.iloc[i - window : i]
        var_values.append(compute_var_ewma(window_slice, confidence, lam))
        actual_values.append(port_returns.iloc[i])
        dates.append(port_returns.index[i])

    var_series = pd.Series(var_values, index=dates, name="var_ewma")
    actual_returns = pd.Series(actual_values, index=dates, name="returns")

    breach_mask = actual_returns < -var_series
    breach_dates = list(actual_returns.index[breach_mask])
    n_breaches = len(breach_dates)
    n_observations = len(var_series)

    return {
        "var_series": var_series,
        "actual_returns": actual_returns,
        "breach_dates": breach_dates,
        "n_breaches": n_breaches,
        "n_observations": n_observations,
        "expected_breaches": n_observations * (1.0 - confidence),
        "kupiec": kupiec_pof_test(n_observations, n_breaches, confidence),
    }
