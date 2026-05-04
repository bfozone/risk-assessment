"""VaR backtesting utilities.

WHAT IS BACKTESTING?
  We test whether our VaR model was accurate in the past.
  The idea: pretend we are at each historical date, estimate VaR using
  only data available *before* that date, then check if the actual return
  that day exceeded our VaR estimate.

ROLLING WINDOW:
  We use a 60-day window. On day 61, we use days 1-60 to estimate VaR,
  then compare against day 61's actual return.
  On day 62, we use days 2-61. And so on.
  This is called "rolling" because the window slides forward each day.

BREACH:
  A breach happens when actual_return < -VaR_estimate.
  (actual return is more negative than the VaR loss threshold)
"""

import pandas as pd

from src.risk_metrics import compute_var_historical, kupiec_pof_test


def run_rolling_backtest(
    port_returns: pd.Series,
    window: int = 60,
    confidence: float = 0.99,
) -> dict:
    """Run a rolling-window historical VaR backtest.

    ALGORITHM (step by step):
      For each day t starting at index `window`:
        1. Take the slice: returns[t-window : t]   ← estimation window
        2. Compute historical VaR on that slice
        3. Look at the actual return on day t
        4. If actual_return < -VaR: it's a breach — record the date

    After iterating all days:
      - Build var_series and actual_returns as pandas Series
      - Count breaches
      - Run Kupiec POF test on the breach count

    Args:
        port_returns: Daily portfolio return series (indexed by date).
        window: Estimation window in days (default: 60).
        confidence: VaR confidence level (default: 0.99 = 99%).

    Returns
    -------
    Dict with:
      var_series      : pd.Series of VaR estimates indexed by date
      actual_returns  : pd.Series of actual returns over the backtest period
      breach_dates    : list of dates where loss exceeded VaR
      n_breaches      : int
      n_observations  : int (number of days in the backtest period)
      expected_breaches: float
      kupiec          : dict (output of kupiec_pof_test)
    """
    var_estimates = {}   # date → VaR estimate for that day
    breach_dates = []    # dates where actual loss > VaR

    # ── Rolling loop ─────────────────────────────────────────────────
    # We start at index `window` so we always have `window` days of history.
    # range(window, len(port_returns)) gives indices: window, window+1, ..., end
    for i in range(window, len(port_returns)):

        # Estimation window: the `window` days BEFORE day i
        estimation_window = port_returns.iloc[i - window : i]

        # Compute VaR from those past returns (positive number = loss threshold)
        var = compute_var_historical(estimation_window, confidence)

        # The date and actual return we are testing against
        current_date = port_returns.index[i]
        actual_return = float(port_returns.iloc[i])

        # Store the VaR estimate for this date
        var_estimates[current_date] = var

        # Check for breach: actual loss (negative return) exceeds VaR
        # actual_return < -var  ↔  loss > var
        if actual_return < -var:
            breach_dates.append(current_date)

    # ── Build output series ──────────────────────────────────────────
    var_series = pd.Series(var_estimates)
    actual_returns = port_returns.iloc[window:]   # the dates we actually tested

    n_observations = len(actual_returns)
    n_breaches = len(breach_dates)
    expected_breaches = n_observations * (1.0 - confidence)

    # ── Kupiec test ──────────────────────────────────────────────────
    kupiec = kupiec_pof_test(n_observations, n_breaches, confidence)

    return {
        "var_series": var_series,
        "actual_returns": actual_returns,
        "breach_dates": breach_dates,
        "n_breaches": n_breaches,
        "n_observations": n_observations,
        "expected_breaches": expected_breaches,
        "kupiec": kupiec,
    }
