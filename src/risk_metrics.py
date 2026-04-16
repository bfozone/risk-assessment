"""Risk metric calculations."""

import numpy as np
import pandas as pd
from scipy.stats import chi2, norm


def compute_var_historical(
    returns: pd.Series,
    confidence: float = 0.99,
) -> float:
    """
    Compute Value-at-Risk using historical simulation.

    Args:
        returns: Series of portfolio returns (not P&L).
        confidence: Confidence level (e.g., 0.99 for 99%).

    Returns:
        VaR as a positive number representing the loss threshold.

    """
    return float(-np.percentile(returns, 100 * (1 - confidence)))


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
    var = compute_var_historical(returns, confidence)
    tail = returns[returns < -var]
    return float(-tail.mean()) if len(tail) > 0 else var


def compute_var_parametric(
    returns: pd.Series,
    confidence: float = 0.99,
) -> float:
    """
    Compute VaR using the variance-covariance (parametric) method.

    Assumes returns are normally distributed.

    Returns:
        VaR as a positive number.

    """
    mu = float(returns.mean())
    sigma = float(returns.std())
    return float(-mu + sigma * norm.ppf(confidence))


def compute_cvar_parametric(
    returns: pd.Series,
    confidence: float = 0.99,
) -> float:
    """
    Compute parametric CVaR assuming normal distribution.

    Returns:
        CVaR as a positive number.

    """
    mu = float(returns.mean())
    sigma = float(returns.std())
    alpha = 1.0 - confidence
    z_alpha = norm.ppf(alpha)
    # E[-Return | Return < -VaR] = -mu + sigma * phi(z_alpha) / alpha
    return float(-mu + sigma * norm.pdf(z_alpha) / alpha)


def compute_component_var(
    weights: np.ndarray,
    cov_matrix: np.ndarray,
    confidence: float = 0.99,
) -> np.ndarray:
    """
    Compute component VaR for each position using Euler decomposition.

    Component VaR decomposes total portfolio VaR into additive contributions.
    The sum of component VaRs equals total portfolio VaR.

    Args:
        weights: Array of portfolio weights.
        cov_matrix: Covariance matrix of asset returns.
        confidence: Confidence level.

    Returns:
        Array of component VaR values (one per asset).

    """
    port_vol = float(np.sqrt(weights @ cov_matrix @ weights))
    marginal_var = (cov_matrix @ weights) / port_vol * norm.ppf(confidence)
    return weights * marginal_var


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
    p0 = 1.0 - confidence
    t = n_observations
    n = n_breaches
    p_hat = n / t if t > 0 else 0.0

    # Likelihood ratio: LR = 2 * [N*log(p_hat/p0) + (T-N)*log((1-p_hat)/(1-p0))]
    # Handle edge cases where p_hat is 0 or 1
    if n == 0:
        lr = 2.0 * t * np.log(1.0 / (1.0 - p0))
    elif n == t:
        lr = 2.0 * (t * np.log(1.0 / p0))
    else:
        lr = 2.0 * (n * np.log(p_hat / p0) + (t - n) * np.log((1.0 - p_hat) / (1.0 - p0)))

    p_value = float(1.0 - chi2.cdf(lr, df=1))

    return {
        "expected_breaches": t * p0,
        "observed_breaches": n,
        "expected_rate": p0,
        "observed_rate": p_hat,
        "test_statistic": float(lr),
        "p_value": p_value,
        "reject_h0": p_value < significance,
    }
