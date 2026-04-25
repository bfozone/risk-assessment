"""Logic for backtesting Risk Metrics - VaR and ES"""

import pandas as pd

from src.risk_metrics import compute_var_historical, kupiec_pof_test, compute_var_ewma

# Historical VaR backtest
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
    clean = port_returns.dropna().copy()
    clean.name = "portfolio_return"

    rows = []

    for i in range(window, len(clean)):
        estimation_window = clean.iloc[i - window:i]
        realized_return = clean.iloc[i]
        date = clean.index[i]

        var_value = compute_var_historical(estimation_window, confidence=confidence)
        breach = realized_return < -var_value

        rows.append({
            "date": pd.Timestamp(date),
            "realized_return": float(realized_return),
            "var_threshold": float(-var_value),
            "breach": bool(breach),
        })

    backtest_df = pd.DataFrame(rows)
    n_obs = len(backtest_df)
    n_breaches = int(backtest_df["breach"].sum())
    breach_dates = (
        backtest_df.loc[backtest_df["breach"], "date"]
        .dt.strftime("%Y-%m-%d")
        .tolist()
    )

    kupiec = kupiec_pof_test(
        n_observations=n_obs,
        n_breaches=n_breaches,
        confidence=confidence,
    )

    return {
        "backtest_df": backtest_df,
        "summary": {
            "model": "historical",
            "breach_dates": breach_dates,
            "n_obs": n_obs,
            "n_breaches": n_breaches,
            "expected_breaches": n_obs * (1.0 - confidence),
            "kupiec_test": kupiec,
        },
    }

# EWMA VaR backtest
def run_rolling_backtest_ewma(
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
    clean = port_returns.dropna().copy()
    clean.name = "portfolio_return"

    rows = []

    for i in range(window, len(clean)):
        estimation_window = clean.iloc[i - window:i]
        realized_return = clean.iloc[i]
        date = clean.index[i]

        var_value = compute_var_ewma(estimation_window, confidence=confidence)
        breach = realized_return < -var_value

        rows.append({
            "date": pd.Timestamp(date),
            "realized_return": float(realized_return),
            "var_threshold": float(-var_value),
            "breach": bool(breach),
        })

    backtest_df = pd.DataFrame(rows)
    n_obs = len(backtest_df)
    n_breaches = int(backtest_df["breach"].sum())
    breach_dates = (
        backtest_df.loc[backtest_df["breach"], "date"]
        .dt.strftime("%Y-%m-%d")
        .tolist()
    )

    kupiec = kupiec_pof_test(
        n_observations=n_obs,
        n_breaches=n_breaches,
        confidence=confidence,
    )

    return {
        "backtest_df": backtest_df,
        "summary": {
            "model": "EWMA VaR (99%)",
            "breach_dates": breach_dates,
            "n_obs": n_obs,
            "n_breaches": n_breaches,
            "expected_breaches": n_obs * (1.0 - confidence),
            "kupiec_test": kupiec,
        },
    }
