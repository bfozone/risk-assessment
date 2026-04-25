"""Risk metrics VaR / ES calculations."""

import numpy as np
import pandas as pd
from scipy.stats import chi2, norm

# Historical VaR / ES

def compute_var_historical(
    returns: pd.Series,
    confidence: float = 0.95,
) -> float:
    """
    Compute Value-at-Risk using historical simulation.

    Args:
        returns: Series of portfolio returns (not P&L).
        confidence: Confidence level (e.g., 0.99 for 99%).

    Returns:
        VaR as a positive number representing the loss threshold.

    """
    clean = returns.dropna()
    alpha = 1.0 - confidence
    var = -np.quantile(clean, alpha)
    return float(max(var, 0.0))




def compute_cvar_historical(
    returns: pd.Series,
    confidence: float = 0.99,
) -> float:
    """
    Compute Conditional VaR (Expected Shortfall) using historical simulation.

    CVaR is the expected loss given that the loss exceeds the VaR threshold.

    Returns:
        CVaR as a positive number.

    """
    clean = returns.dropna()
    alpha = 1.0 - confidence
    cutoff = np.quantile(clean, alpha)
    tail = clean[clean <= cutoff]
    cvar = -tail.mean()
    return float(max(cvar, 0.0))



# Parametric VaR / ES

def compute_var_parametric(
    returns: pd.Series,
    confidence: float = 0.95,
) -> float:
    """
    Compute VaR using the variance-covariance (parametric) method.

    Assumes returns are normally distributed.

    Returns:
        VaR as a positive number.

    """
    clean = returns.dropna()
    mu = clean.mean()
    sigma = clean.std(ddof=1)
    z = norm.ppf(1.0 - confidence)
    var = -(mu + z * sigma)
    return float(max(var, 0.0))




def compute_cvar_parametric(
    returns: pd.Series,
    confidence: float = 0.99,
) -> float:
    """
    Compute parametric CVaR assuming normal distribution.

    Returns:
        CVaR as a positive number.

    """
    clean = returns.dropna()
    mu = clean.mean()
    sigma = clean.std(ddof=1)

    alpha = 1.0 - confidence
    z_alpha = norm.ppf(alpha)

    cvar = -(mu - sigma * norm.pdf(z_alpha) / alpha)
    return float(max(cvar, 0.0))


# Component VaR

def compute_component_var(
    returns_wide: pd.DataFrame,
    positions: pd.DataFrame,
    confidence: float = 0.95,
) -> pd.DataFrame:
    """
    Parametric Euler-style component VaR grouped by sub_class.
    Assumes:
    - returns_wide columns = instrument_id
    - positions has instrument_id, weight, sub_class
    """
    pos = positions[["instrument_id", "weight", "sub_class"]].copy()
    pos = pos[pos["instrument_id"].isin(returns_wide.columns)]

    cols = list(pos["instrument_id"])
    X = returns_wide[cols].dropna()
    w = pos.set_index("instrument_id")["weight"].loc[cols].values

    cov = X.cov().values
    portfolio_vol = np.sqrt(w @ cov @ w)
    z = norm.ppf(confidence)

    marginal_vol = cov @ w / portfolio_vol
    component_vol = w * marginal_vol
    component_var = z * component_vol

    out = pd.DataFrame({
        "instrument_id": cols,
        "component_var": component_var,
    }).merge(pos, on="instrument_id", how="left")

    grouped = (
        out.groupby("sub_class", as_index=False)["component_var"]
        .sum()
        .sort_values("component_var", ascending=False)
        .reset_index(drop=True)
    )
    return grouped

# Kupiec test
def kupiec_pof_test(
    n_observations: int,
    n_breaches: int,
    confidence: float = 0.99,
    significance: float = 0.05,
) -> dict:
    """
    Kupiec Proportion of Failures (POF) test for VaR backtesting.

    Tests H0: the observed breach rate is consistent with the expected rate.

    Args:
        n_observations: Number of days in the backtest period.
        n_breaches: Number of observed VaR breaches.
        confidence: VaR confidence level.
        significance: Significance level for hypothesis test.

    Returns:
        Dictionary with keys: expected_breaches, observed_breaches,
        expected_rate, observed_rate, test_statistic, p_value, reject_h0

    """

    if n_observations <= 0:
        raise ValueError("n_obs must be positive")
    if not (0 <= n_breaches <= n_observations):
        raise ValueError("n_breaches must be between 0 and n_obs")

    p = 1.0 - confidence
    x = n_breaches
    n = n_observations
    phat = x / n if n > 0 else 0.0

    if phat == 0:
        phat = 1e-12
    elif phat == 1:
        phat = 1 - 1e-12

    lr_stat = -2.0 * (
        (n - x) * np.log((1 - p) / (1 - phat))
        + x * np.log(p / phat)
    )
    p_value = 1.0 - chi2.cdf(lr_stat, df=1)

    return {
        "n_obs": int(n_observations),
        "n_breaches": int(n_breaches),
        "expected_breach_rate": float(p),
        "observed_breach_rate": float(n_breaches / n_observations),
        "lr_stat": float(lr_stat),
        "p_value": float(p_value),
        "reject_95pct": bool(p_value < 0.05),
    }

# Important: the Kupiec rejection forces me to implement one of the alternatives to address the drawbacks of the Historical VaR. See below
# See also the backtest.py file where the backtest approach is described.

# EWMA VaR
# In this case the older price observations decay esponentially and the most recent ones are getting more relevance / weight
# We need two functions: one for the EWMA volatility series and one for the calculation of the VaR.
# The lambda of 0.94 is a common choice as a decay factor.

def compute_ewma_volatility(
    returns: pd.Series,
    lambda_: float = 0.94,
) -> pd.Series:
    """
    Compute EWMA volatility series.

    Args:
        returns: portfolio returns
        lambda_: decay factor

    Returns:
        Series of EWMA volatility
    """
    returns = returns.dropna()

    if len(returns) < 2:
        raise ValueError("Not enough returns to compute EWMA volatility.")

    var = np.zeros(len(returns))

    # Better initialization: use a short recent window instead of full-sample variance
    init_window = min(20, len(returns))
    var[0] = returns.iloc[:init_window].var()

    for t in range(1, len(returns)):
        var[t] = lambda_ * var[t - 1] + (1 - lambda_) * returns.iloc[t - 1] ** 2

    vol = np.sqrt(var)
    return pd.Series(vol, index=returns.index)


def compute_var_ewma(
    returns: pd.Series,
    confidence: float = 0.99,
    lambda_: float = 0.94,
) -> float:
    """
    Compute EWMA-based VaR.

    Args:
        returns: portfolio returns
        confidence: VaR confidence level
        lambda_: EWMA decay factor

    Returns:
        VaR (positive number)
    """
    clean = returns.dropna()

    if len(clean) < 2:
        raise ValueError("Not enough returns to compute EWMA VaR.")

    vol_series = compute_ewma_volatility(clean, lambda_)

    sigma = vol_series.iloc[-1]

    z = norm.ppf(1 - confidence)
    var = -z * sigma

    return float(max(var, 0.0))