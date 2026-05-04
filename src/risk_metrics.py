"""Risk metric calculations."""

import numpy as np
import pandas as pd
from scipy.stats import norm, chi2


def compute_var_historical(
    returns: pd.Series,
    confidence: float = 0.99,) -> float:
    """Compute Value-at-Risk using historical simulation.
    Args:
        returns: Series of daily portfolio returns (e.g. 0.01 = +1%).
        confidence: e.g. 0.99 for 99% VaR.
    Returns
    VaR as a positive number (a loss magnitude).
    """
    # np.quantile at (1 - confidence) gives the left tail value (a negative number).
    # We negate it to express as a positive loss.
    return -float(np.quantile(returns, 1.0 - confidence))


def compute_cvar_historical(
    returns: pd.Series,
    confidence: float = 0.99,) -> float:
    
    """Compute Conditional VaR (Expected Shortfall) using historical simulation.
    Returns: CVaR as a positive number.
    """
    var = compute_var_historical(returns, confidence)
    # Select only the tail: returns that are worse (more negative) than -VaR
    tail_returns = returns[returns < -var]

    if len(tail_returns) == 0:
        # Edge case: no tail observations — CVaR equals VaR
        return var

    return -float(tail_returns.mean())


def compute_var_parametric(
    returns: pd.Series,
    confidence: float = 0.99,) -> float:

    """Compute VaR using the parametric (variance-covariance) method.
    ASSUMPTION: returns follow a Normal (Gaussian) distribution.

    FORMULA:
      VaR = -(mu - z * sigma)
           = -mu + z * sigma

    WHERE:
      mu    = mean of returns
      sigma = standard deviation of returns
      z     = norm.ppf(confidence) — the z-score at the given confidence level
              For 99%, z ≈ 2.326.  For 95%, z ≈ 1.645.

    Returns
    -------
    VaR as a positive number.
    """
    mu = float(returns.mean())
    sigma = float(returns.std())
    z = norm.ppf(confidence)  # e.g., 2.326 for 99%
    return -mu + z * sigma



def compute_cvar_parametric(
    returns: pd.Series,
    confidence: float = 0.99,
) -> float:
    """Compute parametric CVaR assuming normally distributed returns.

    FORMULA (normal distribution):
      CVaR = -mu + sigma * phi(z) / (1 - confidence)

    WHERE:
      phi(z) = norm.pdf(z) — the height of the normal curve at z
              This gives the density of the tail, which when divided by
              the tail probability (1 - confidence) gives the average tail loss.

    INTUITION:
      Think of CVaR as: "the parametric average of everything beyond VaR".
      norm.pdf(z) / (1 - confidence) is a scaling factor that converts
      the tail area into an average loss magnitude.

    Returns
    -------
    CVaR as a positive number.
    """
    mu = float(returns.mean())
    sigma = float(returns.std())
    z = norm.ppf(confidence)
    # norm.pdf(z) = phi(z) = height of the standard normal curve at z
    cvar = -mu + sigma * norm.pdf(z) / (1.0 - confidence)
    return cvar


def _ewma_weights(n: int, decay: float) -> np.ndarray:
    """Compute EWMA weights for n observations, newest observation last.

    WHAT ARE EWMA WEIGHTS?
      In plain historical VaR, every past return counts equally.
      EWMA (Exponentially Weighted Moving Average) instead gives
      more weight to recent returns and less to old ones.

      The weight for a return that is k days ago is proportional to λ^k,
      where λ (lambda) is the decay factor (e.g. 0.99 or 0.97).

      λ = 0.99 → slow decay: yesterday counts 1% more than two days ago.
                 Old data fades slowly. Good for capturing long-run risk.
      λ = 0.97 → faster decay: recent data matters much more.
                 Reacts more quickly to volatility spikes (or calm periods).

    HOW WE BUILD THE WEIGHT VECTOR:
      We have returns[0], returns[1], ..., returns[n-1], newest last.
      The most recent return (index n-1) gets weight λ^0 = 1.
      The one before (index n-2) gets weight λ^1.
      The oldest (index 0) gets weight λ^(n-1).

      Written as a formula for index i (0 = oldest, n-1 = newest):
        raw_weight[i] = λ^(n-1-i)

      Then we normalise so weights sum to 1:
        weight[i] = raw_weight[i] / sum(raw_weights)

      For large n and λ < 1 this normalisation factor ≈ 1 / (1 - λ),
      but we compute it exactly to be precise.

    Args:
        n: Number of observations.
        decay: Decay factor λ ∈ (0, 1).

    Returns
    -------
    Array of n weights summing to 1.0, oldest first.
    """
    # Exponents: oldest gets (n-1), newest gets 0
    exponents = np.arange(n - 1, -1, -1, dtype=float)   # [n-1, n-2, ..., 1, 0]
    raw = decay ** exponents                              # λ^(n-1), λ^(n-2), ..., 1
    return raw / raw.sum()                               # normalise to sum = 1


def compute_var_ewma(
    returns: pd.Series,
    confidence: float = 0.99,
    decay: float = 0.97,
) -> float:
    """Compute EWMA-weighted historical VaR.

    METHOD — weighted quantile:
      1. Compute EWMA weights (recent days get higher weight).
      2. Sort returns from worst to best, carrying their weights along.
      3. Walk from the worst return upward, accumulating weights.
      4. The VaR is the return at which cumulative weight crosses (1 - confidence).

    Args:
        returns: Series of daily returns (newest last, or date-indexed).
        confidence: Confidence level (e.g. 0.99).
        decay: EWMA decay factor λ (e.g. 0.99 or 0.97).

    Returns
    -------
    VaR as a positive number (loss magnitude).
    """
    r = np.asarray(returns, dtype=float)
    n = len(r)
    weights = _ewma_weights(n, decay)

    # Sort returns ascending (worst loss first), keeping weights aligned
    sort_idx = np.argsort(r)
    sorted_returns = r[sort_idx]
    sorted_weights = weights[sort_idx]

    # Accumulate weights from the left (worst returns first).
    # The VaR is the return where the cumulative weight first reaches (1-confidence).
    cumulative_weights = np.cumsum(sorted_weights)
    tail_prob = 1.0 - confidence   # e.g. 0.01

    # Find the first index where cumulative weight >= tail probability
    idx = np.searchsorted(cumulative_weights, tail_prob)
    # Clamp to valid range (defensive)
    idx = min(idx, n - 1)

    return -float(sorted_returns[idx])


def compute_cvar_ewma(
    returns: pd.Series,
    confidence: float = 0.99,
    decay: float = 0.97,
) -> float:
    """Compute EWMA-weighted CVaR (Expected Shortfall).

    METHOD:
      1. Compute EWMA weights and VaR threshold.
      2. Identify which returns are in the tail (return < -VaR).
      3. Compute their weighted average: sum(w_i * r_i) / sum(w_i) for tail.
      4. Negate to report as a positive loss.

    Returns
    -------
    CVaR as a positive number.
    """
    r = np.asarray(returns, dtype=float)
    n = len(r)
    weights = _ewma_weights(n, decay)

    var = compute_var_ewma(returns, confidence, decay)
    tail_prob = 1.0 - confidence

    # Select tail observations: those with return < -VaR
    tail_mask = r < -var

    if not tail_mask.any():
        return var   # edge case: no tail observations

    tail_returns = r[tail_mask]
    tail_weights = weights[tail_mask]

    # Normalise tail weights to sum to 1 within the tail
    # (otherwise the weighted average is distorted by the total weight in the tail)
    tail_weights_norm = tail_weights / tail_weights.sum()

    weighted_mean_loss = float(np.dot(tail_weights_norm, tail_returns))
    return -weighted_mean_loss



def compute_component_var(
    weights: np.ndarray,
    cov_matrix: np.ndarray,
    confidence: float = 0.99,
) -> np.ndarray:
    """Compute component VaR using the Euler decomposition.

    WHAT IS COMPONENT VaR?
      It tells you how much each position *contributes* to total portfolio VaR.
      Key property: component VaRs sum exactly to total portfolio VaR.
      This lets you say "Swiss equities account for 40% of our risk".

    THE MATHS (step by step):
      1. Portfolio variance:   var_p = w' @ Σ @ w
         (w = weights vector, Σ = covariance matrix, ' = transpose)

      2. Portfolio volatility: σ_p = sqrt(var_p)

      3. Portfolio VaR:        VaR_p = z * σ_p
         (z = norm.ppf(confidence))

      4. Marginal volatility:  ∂σ_p/∂w_i = (Σ @ w)_i / σ_p
         This is how much σ_p changes if you add a tiny bit more of asset i.

      5. Component VaR:        CVaR_i = w_i * z * (Σ @ w)_i / σ_p
         = weight × z-score × marginal volatility contribution

    WHY IT WORKS (Euler's theorem):
      For a function that scales linearly (like σ_p = sqrt(w'Σw)),
      the sum of (w_i × ∂f/∂w_i) equals f itself.
      So sum(component_var_i) = VaR_p exactly.

    Args:
        weights: Array of portfolio weights summing to 1.
        cov_matrix: Covariance matrix of asset returns.
        confidence: Confidence level.

    Returns
    -------
    Array of component VaR values (one per asset).
    """
    weights = np.asarray(weights, dtype=float)
    cov_matrix = np.asarray(cov_matrix, dtype=float)

    # Step 1 & 2: portfolio volatility
    port_variance = float(weights @ cov_matrix @ weights)
    port_vol = np.sqrt(port_variance)

    # Step 3: z-score
    z = norm.ppf(confidence)

    # Step 4: marginal volatility contribution per asset
    # (cov_matrix @ weights) gives a vector; dividing by port_vol normalises
    marginal_vol = (cov_matrix @ weights) / port_vol

    # Step 5: component VaR = weight × z × marginal_vol
    component_var = weights * z * marginal_vol

    return component_var



def kupiec_pof_test(
    n_observations: int,
    n_breaches: int,
    confidence: float = 0.99,
    significance: float = 0.05,
) -> dict:
    """Kupiec Proportion of Failures (POF) test for VaR model validation.

    WHAT IS A VaR BREACH?
      A breach happens when the actual daily loss EXCEEDS the VaR estimate.
      At 99% confidence, we expect 1% of days to be breaches.
      With 250 trading days, we expect 2.5 breaches per year.

    WHAT DOES THIS TEST DO?
      It asks: "Is our observed breach rate consistent with the model?"
      H0 (null hypothesis): breach rate = (1 - confidence), i.e. model is correct.
      If we see too many or too few breaches, we reject H0.

    HOW IT WORKS — Likelihood Ratio test:
      LR = 2 * [ N*ln(N/(T*p)) + (T-N)*ln((T-N)/(T*(1-p))) ]

      WHERE:
        T = n_observations (total days)
        N = n_breaches
        p = 1 - confidence (expected breach rate)

      Under H0, LR follows a chi-squared distribution with 1 degree of freedom.
      p_value = P(chi2(1) > LR)
      If p_value < significance → reject H0 (model is miscalibrated).

    KNOWN RESULTS:
      2 breaches in 250 days at 99%: LR ≈ 0.10 → p_value ≈ 0.75 → do NOT reject ✓
      10 breaches in 250 days at 99%: LR ≈ 13 → p_value ≈ 0.0003 → REJECT ✓

    Args:
        n_observations: Total number of days in the backtest window.
        n_breaches: Number of days where loss exceeded VaR.
        confidence: VaR confidence level (e.g. 0.99).
        significance: Significance threshold (e.g. 0.05 for 5%).

    Returns
    -------
    Dict with: expected_breaches, observed_breaches, expected_rate,
    observed_rate, test_statistic, p_value, reject_h0
    """
    T = n_observations
    N = n_breaches
    p = 1.0 - confidence      # expected breach probability (e.g. 0.01)

    expected_breaches = T * p
    observed_rate = N / T if T > 0 else 0.0

    # ── Compute the likelihood ratio statistic ───────────────────────
    # Handle edge cases where N=0 or N=T (log(0) is undefined)
    if N == 0:
        # All days: no breach. LR simplifies to:
        lr = 2.0 * T * np.log(1.0 / (1.0 - p))
    elif N == T:
        # All days were breaches. LR simplifies to:
        lr = 2.0 * T * np.log(1.0 / p)
    else:
        # General case
        lr = 2.0 * (
            N * np.log(N / (T * p))
            + (T - N) * np.log((T - N) / (T * (1.0 - p)))
        )

    # ── p-value from chi-squared distribution (1 degree of freedom) ─
    p_value = float(1.0 - chi2.cdf(lr, df=1))
    reject_h0 = p_value < significance

    return {
        "expected_breaches": expected_breaches,
        "observed_breaches": N,
        "expected_rate": p,
        "observed_rate": observed_rate,
        "test_statistic": float(lr),
        "p_value": p_value,
        "reject_h0": bool(reject_h0),
    }
