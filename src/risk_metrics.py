"""Risk metric calculations."""

import numpy as np
import pandas as pd


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
    raise NotImplementedError


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
    raise NotImplementedError


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
    raise NotImplementedError


def compute_cvar_parametric(
    returns: pd.Series,
    confidence: float = 0.99,
) -> float:
    """
    Compute parametric CVaR assuming normal distribution.

    Returns:
        CVaR as a positive number.

    """
    raise NotImplementedError


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
    raise NotImplementedError


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
    raise NotImplementedError
