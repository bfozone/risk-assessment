"""Risk metric calculations."""

import numpy as np
import pandas as pd
from scipy.stats import binom, chi2, norm


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


def compute_var_ewma(
    returns: pd.Series,
    confidence: float = 0.99,
    lam: float = 0.94,
) -> float:
    """
    Filtered Historical Simulation VaR using EWMA volatility scaling (Hull-White 1998).

    Rescales each historical return by the ratio of the one-step-ahead EWMA
    volatility forecast to the EWMA vol at the time of that observation, then
    takes the quantile of the scaled returns.  This reacts faster to volatility
    regime shifts than flat historical simulation.

    Args:
        returns: Series of portfolio returns.
        confidence: VaR confidence level.
        lam: EWMA decay factor (0.94 = RiskMetrics daily standard).

    Returns:
        VaR as a positive number.

    """
    r = np.asarray(returns, dtype=float)
    n = len(r)
    sigma2 = np.empty(n)
    sigma2[0] = float(np.var(r))
    for i in range(1, n):
        sigma2[i] = lam * sigma2[i - 1] + (1.0 - lam) * r[i - 1] ** 2
    sigma2_forecast = lam * sigma2[-1] + (1.0 - lam) * r[-1] ** 2
    sigma_forecast = float(np.sqrt(sigma2_forecast))
    sigma_hist = np.sqrt(np.maximum(sigma2, 1e-12))
    scaled = r * sigma_forecast / sigma_hist
    return float(-np.percentile(scaled, 100.0 * (1.0 - confidence)))


def christoffersen_independence_test(
    breach_indicator: pd.Series,
) -> dict:
    """
    Christoffersen (1998) independence test for VaR breach clustering.

    Tests H0: breach occurrences are independent across successive days.
    A clustered sequence violates the iid Bernoulli assumption underlying
    historical VaR and signals a volatility-regime failure mode.

    Args:
        breach_indicator: Binary series (1 = breach, 0 = no breach).

    Returns:
        Dictionary with transition counts, transition probabilities,
        LR statistic, p-value, and reject_h0 flag.

    """
    b: np.ndarray = breach_indicator.astype(int).to_numpy()
    n00 = int(np.sum((b[:-1] == 0) & (b[1:] == 0)))
    n01 = int(np.sum((b[:-1] == 0) & (b[1:] == 1)))
    n10 = int(np.sum((b[:-1] == 1) & (b[1:] == 0)))
    n11 = int(np.sum((b[:-1] == 1) & (b[1:] == 1)))

    pi_01 = n01 / (n00 + n01) if (n00 + n01) > 0 else 0.0
    pi_11 = n11 / (n10 + n11) if (n10 + n11) > 0 else 0.0
    pi_hat = (n01 + n11) / (n00 + n01 + n10 + n11) if (n00 + n01 + n10 + n11) > 0 else 0.0

    def _slog(x: float) -> float:
        return float(np.log(x)) if x > 0 else 0.0

    lr_ind = 2.0 * (
        n00 * _slog(1.0 - pi_01)
        + n01 * _slog(pi_01)
        + n10 * _slog(1.0 - pi_11)
        + n11 * _slog(pi_11)
        - (n00 + n10) * _slog(1.0 - pi_hat)
        - (n01 + n11) * _slog(pi_hat)
    )
    p_ind = float(1.0 - chi2.cdf(lr_ind, df=1))

    return {
        "n00": n00,
        "n01": n01,
        "n10": n10,
        "n11": n11,
        "pi_01": pi_01,
        "pi_11": pi_11,
        "pi_hat": pi_hat,
        "lr_independence": float(lr_ind),
        "p_independence": p_ind,
        "reject_independence": p_ind < 0.05,
    }


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


def basel_traffic_light(
    n_observations: int,
    n_breaches: int,
    confidence: float = 0.99,
) -> dict:
    """
    Basel Committee traffic light for VaR model validation.

    Original calibration: 250 trading days, 99% VaR.
      Green  (0-4 breaches): model likely correct.
      Yellow (5-9 breaches): model suspect - capital multiplier add-on.
      Red    (>=10 breaches): model rejected - mandatory review.

    For non-standard sample sizes the zone boundaries are re-derived from
    the same binomial CDF levels used in the Basel calibration
    (CDF(4) ≈ 0.8909 and CDF(9) ≈ 0.9999 under Binom(250, 0.01)).

    Returns:
        Dictionary with zone, thresholds, capital add-on, and Basel reference
        thresholds for a 250-day period.

    """
    p0 = 1.0 - confidence
    green_max = int(binom.ppf(0.8909, n_observations, p0))
    yellow_max = int(binom.ppf(0.9999, n_observations, p0))

    if n_breaches <= green_max:
        zone = "green"
        addon = 0.00
    elif n_breaches <= yellow_max:
        zone = "yellow"
        zone_width = max(yellow_max - green_max, 1)
        excess = n_breaches - green_max
        addon = round(0.40 + 0.45 * (excess - 1) / max(zone_width - 1, 1), 2)
        addon = min(addon, 0.85)
    else:
        zone = "red"
        addon = 1.00

    return {
        "zone": zone,
        "n_breaches": n_breaches,
        "green_max": green_max,
        "yellow_max": yellow_max,
        "capital_multiplier_addon": addon,
        "basel_reference": {
            "sample_days": 250,
            "green_max": 4,
            "yellow_max": 9,
        },
    }


def es_coverage_test(
    actual_returns: pd.Series,
    var_series: pd.Series,
    es_series: pd.Series,
    n_bootstrap: int = 5000,
    seed: int = 42,
) -> dict:
    """
    Practical ES coverage test via bootstrap.

    On breach days the average realized loss should equal the model's ES
    estimate (coverage ratio ≈ 1.0).  A ratio significantly above 1.0
    indicates the model systematically underestimates tail severity.

    Rejects H0 when the entire 95% bootstrap CI lies above 1.0.

    Args:
        actual_returns: Realised daily return series.
        var_series: Rolling VaR estimates (positive = loss threshold).
        es_series: Rolling ES/CVaR estimates (positive).
        n_bootstrap: Number of bootstrap resamples.
        seed: Random seed for reproducibility.

    Returns:
        Dictionary with breach count, mean realized loss, mean ES estimate,
        coverage ratio, bootstrap CI, and reject_h0 flag.

    """
    breach_mask = actual_returns < -var_series
    breach_returns = actual_returns[breach_mask]
    breach_es = es_series[breach_mask]

    if len(breach_returns) == 0:
        nan = float("nan")
        return {
            "n_breach_days": 0,
            "mean_realized_loss": nan,
            "mean_es_estimate": nan,
            "es_coverage_ratio": nan,
            "bootstrap_ci_95": (nan, nan),
            "reject_h0": False,
        }

    mean_loss = float(-breach_returns.mean())
    mean_es = float(breach_es.mean())
    ratio = mean_loss / mean_es if mean_es > 0.0 else float("nan")

    rng = np.random.default_rng(seed)
    n = len(breach_returns)
    boot_ratios = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        b_loss = float(-breach_returns.iloc[idx].mean())
        b_es = float(breach_es.iloc[idx].mean())
        if b_es > 0.0:
            boot_ratios.append(b_loss / b_es)

    arr = np.array(boot_ratios)
    ci = (float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5)))

    return {
        "n_breach_days": n,
        "mean_realized_loss": mean_loss,
        "mean_es_estimate": mean_es,
        "es_coverage_ratio": ratio,
        "bootstrap_ci_95": ci,
        "reject_h0": bool(ci[0] > 1.0),
    }
