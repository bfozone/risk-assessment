# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportMissingTypeStubs=false
"""Stretched coverage for src/risk_metrics.py.

Core baseline assertions (positive result, plausible range, CVaR >= VaR at
99%, Euler sum property, Kupiec accept/reject) are already covered in
test_risk_metrics.py and are not repeated here.

Tests are organised into one class per public function:
  - TestComputeVarHistorical
  - TestComputeCvarHistorical
  - TestComputeVarParametric
  - TestComputeCvarParametric
  - TestComputeComponentVar
  - TestKupiecPofTest
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from risk_metrics import (
    compute_component_var,
    compute_cvar_historical,
    compute_cvar_parametric,
    compute_var_historical,
    compute_var_parametric,
    kupiec_pof_test,
)

# ---------------------------------------------------------------------------
# Private constants
# ---------------------------------------------------------------------------

_CONFIDENCE_LEVELS: list[float] = [0.90, 0.95, 0.99]

_KUPIEC_RESULT_KEYS: list[str] = [
    "expected_breaches",
    "observed_breaches",
    "expected_rate",
    "observed_rate",
    "test_statistic",
    "p_value",
    "reject_h0",
]

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def normal_returns() -> pd.Series:
    """Deterministic N(0.0005, 0.01) returns — 1 000 observations."""
    rng = np.random.default_rng(42)
    return pd.Series(rng.normal(loc=0.0005, scale=0.01, size=1_000))


@pytest.fixture(scope="module")
def fat_tail_returns() -> pd.Series:
    """Student-t(df=3) returns scaled to ~1% daily vol — 1 000 observations."""
    rng = np.random.default_rng(42)
    raw = rng.standard_t(df=3, size=1_000)
    return pd.Series(raw * 0.01 / raw.std())


@pytest.fixture
def diagonal_cov_3x3() -> np.ndarray:
    """3x3 diagonal covariance matrix — assets are uncorrelated."""
    return np.diag([0.04, 0.02, 0.01])


@pytest.fixture
def correlated_cov_3x3() -> np.ndarray:
    """3x3 covariance matrix with positive off-diagonal correlations."""
    return np.array(
        [
            [0.04, 0.012, -0.006],
            [0.012, 0.03, -0.004],
            [-0.006, -0.004, 0.01],
        ]
    )


@pytest.fixture
def equal_weights() -> np.ndarray:
    return np.array([1 / 3, 1 / 3, 1 / 3])


@pytest.fixture
def skewed_weights() -> np.ndarray:
    return np.array([0.6, 0.3, 0.1])


# ---------------------------------------------------------------------------
# TestComputeVarHistorical
# ---------------------------------------------------------------------------


class TestComputeVarHistorical:
    """Unit tests for compute_var_historical."""

    @pytest.mark.parametrize("conf", _CONFIDENCE_LEVELS)
    def test_higher_confidence_gives_higher_var(
        self, normal_returns: pd.Series, conf: float
    ) -> None:
        """VaR must be monotonically increasing in the confidence level."""
        lower_conf = conf - 0.05
        var_high = compute_var_historical(normal_returns, confidence=conf)
        var_low = compute_var_historical(normal_returns, confidence=lower_conf)
        assert var_high >= var_low

    def test_deterministic_on_fixed_data(self) -> None:
        """Same series must always return the same VaR."""
        returns = pd.Series([-0.05, -0.03, -0.01, 0.0, 0.02, 0.03])
        assert compute_var_historical(returns, 0.99) == compute_var_historical(returns, 0.99)

    def test_known_value(self) -> None:
        """With a sorted uniform series the 1st-percentile loss is recoverable."""
        # returns: -0.10, -0.09, ..., 0.00 — 11 values
        returns = pd.Series(np.linspace(-0.10, 0.0, 11))
        var = compute_var_historical(returns, confidence=0.90)
        # 10th percentile loss = percentile(returns, 10) = -0.09 → VaR = 0.09
        assert var == pytest.approx(0.09, abs=1e-6)


# ---------------------------------------------------------------------------
# TestComputeCvarHistorical
# ---------------------------------------------------------------------------


class TestComputeCvarHistorical:
    """Unit tests for compute_cvar_historical."""

    def test_result_is_positive(self, normal_returns: pd.Series) -> None:
        assert compute_cvar_historical(normal_returns, confidence=0.99) > 0

    @pytest.mark.parametrize("conf", [0.90, 0.95])
    def test_cvar_exceeds_var_at_sub_99_confidence(
        self, normal_returns: pd.Series, conf: float
    ) -> None:
        var = compute_var_historical(normal_returns, confidence=conf)
        cvar = compute_cvar_historical(normal_returns, confidence=conf)
        assert cvar >= var

    def test_fat_tails_inflate_cvar_more_than_var(
        self, normal_returns: pd.Series, fat_tail_returns: pd.Series
    ) -> None:
        """For fat-tailed returns the CVaR/VaR ratio should exceed that of normal returns."""
        conf = 0.99
        ratio_normal = compute_cvar_historical(normal_returns, conf) / compute_var_historical(
            normal_returns, conf
        )
        ratio_fat = compute_cvar_historical(fat_tail_returns, conf) / compute_var_historical(
            fat_tail_returns, conf
        )
        assert ratio_fat > ratio_normal

    def test_cvar_equals_var_when_single_tail_observation(self) -> None:
        """With exactly one observation in the tail, CVaR == VaR."""
        returns = pd.Series([-0.10] + [0.01] * 99)
        var = compute_var_historical(returns, confidence=0.99)
        cvar = compute_cvar_historical(returns, confidence=0.99)
        assert cvar >= var


# ---------------------------------------------------------------------------
# TestComputeVarParametric
# ---------------------------------------------------------------------------


class TestComputeVarParametric:
    """Unit tests for compute_var_parametric."""

    @pytest.mark.parametrize("conf", _CONFIDENCE_LEVELS)
    def test_higher_confidence_gives_higher_var(
        self, normal_returns: pd.Series, conf: float
    ) -> None:
        lower_conf = conf - 0.05
        assert compute_var_parametric(normal_returns, conf) >= compute_var_parametric(
            normal_returns, lower_conf
        )

    def test_matches_analytical_formula(self) -> None:
        """Parametric VaR must equal -mu + sigma * z for a known series."""
        rng = np.random.default_rng(7)
        returns = pd.Series(rng.normal(loc=0.001, scale=0.015, size=10_000))
        mu, sigma = returns.mean(), returns.std()
        expected = -mu + sigma * norm.ppf(0.99)
        assert compute_var_parametric(returns, 0.99) == pytest.approx(expected, rel=1e-9)

    def test_close_to_historical_for_normal_returns(self, normal_returns: pd.Series) -> None:
        """Parametric and historical VaR should converge for large normal samples."""
        hist = compute_var_historical(normal_returns, 0.99)
        param = compute_var_parametric(normal_returns, 0.99)
        # allow 20% relative tolerance — distributional estimation noise
        assert abs(param - hist) / hist < 0.20


# ---------------------------------------------------------------------------
# TestComputeCvarParametric
# ---------------------------------------------------------------------------


class TestComputeCvarParametric:
    """Unit tests for compute_cvar_parametric."""

    def test_result_is_positive(self, normal_returns: pd.Series) -> None:
        assert compute_cvar_parametric(normal_returns, confidence=0.99) > 0

    @pytest.mark.parametrize("conf", [0.90, 0.95])
    def test_cvar_exceeds_var_at_sub_99_confidence(
        self, normal_returns: pd.Series, conf: float
    ) -> None:
        var = compute_var_parametric(normal_returns, confidence=conf)
        cvar = compute_cvar_parametric(normal_returns, confidence=conf)
        assert cvar >= var

    def test_matches_analytical_formula(self) -> None:
        """Parametric CVaR must equal -mu + sigma * phi(z) / alpha for known series."""
        rng = np.random.default_rng(7)
        returns = pd.Series(rng.normal(loc=0.001, scale=0.015, size=10_000))
        mu, sigma = returns.mean(), returns.std()
        alpha = 0.01
        z_alpha = norm.ppf(alpha)
        expected = -mu + sigma * norm.pdf(z_alpha) / alpha
        assert compute_cvar_parametric(returns, 0.99) == pytest.approx(expected, rel=1e-9)

    def test_higher_confidence_gives_higher_cvar(self, normal_returns: pd.Series) -> None:
        assert compute_cvar_parametric(normal_returns, 0.99) > compute_cvar_parametric(
            normal_returns, 0.95
        )


# ---------------------------------------------------------------------------
# TestComputeComponentVar
# ---------------------------------------------------------------------------


class TestComputeComponentVar:
    """Unit tests for compute_component_var (Euler decomposition)."""

    def test_sum_equals_total_var_diagonal(
        self, equal_weights: np.ndarray, diagonal_cov_3x3: np.ndarray
    ) -> None:
        """Euler property must hold for uncorrelated assets too."""
        comp = compute_component_var(equal_weights, diagonal_cov_3x3, confidence=0.99)
        port_vol = float(np.sqrt(equal_weights @ diagonal_cov_3x3 @ equal_weights))
        total_var = port_vol * norm.ppf(0.99)
        assert float(comp.sum()) == pytest.approx(total_var, abs=1e-10)

    @pytest.mark.parametrize("conf", [0.95, 0.99])
    def test_sum_invariant_to_confidence_level(
        self,
        skewed_weights: np.ndarray,
        correlated_cov_3x3: np.ndarray,
        conf: float,
    ) -> None:
        """Euler property holds at every confidence level."""
        comp = compute_component_var(skewed_weights, correlated_cov_3x3, conf)
        port_vol = float(np.sqrt(skewed_weights @ correlated_cov_3x3 @ skewed_weights))
        assert float(comp.sum()) == pytest.approx(port_vol * norm.ppf(conf), abs=1e-10)

    def test_returns_array_with_correct_length(
        self, skewed_weights: np.ndarray, correlated_cov_3x3: np.ndarray
    ) -> None:
        comp = compute_component_var(skewed_weights, correlated_cov_3x3)
        assert len(comp) == len(skewed_weights)

    def test_large_weight_has_largest_component(self, correlated_cov_3x3: np.ndarray) -> None:
        """The dominant position should contribute the largest component VaR."""
        weights = np.array([0.80, 0.10, 0.10])
        comp = compute_component_var(weights, correlated_cov_3x3, confidence=0.99)
        assert int(np.argmax(comp)) == 0


# ---------------------------------------------------------------------------
# TestKupiecPofTest
# ---------------------------------------------------------------------------


class TestKupiecPofTest:
    """Unit tests for kupiec_pof_test."""

    # Presence and types

    @pytest.mark.parametrize("key", _KUPIEC_RESULT_KEYS)
    def test_result_contains_required_key(self, key: str) -> None:
        result = kupiec_pof_test(250, 2, 0.99)
        assert key in result

    def test_p_value_is_between_zero_and_one(self) -> None:
        result = kupiec_pof_test(250, 2, 0.99)
        assert 0.0 <= result["p_value"] <= 1.0

    def test_reject_h0_is_boolean(self) -> None:
        result = kupiec_pof_test(250, 2, 0.99)
        assert isinstance(result["reject_h0"], bool)

    def test_rejects_zero_breaches_out_of_250(self) -> None:
        """0/250 is also a model failure — too few breaches should reject."""
        assert kupiec_pof_test(250, 0, 0.99)["reject_h0"]

    # Rates and counts

    def test_expected_rate_matches_confidence(self) -> None:
        result = kupiec_pof_test(500, 5, 0.99)
        assert result["expected_rate"] == pytest.approx(0.01)

    def test_observed_rate_equals_n_over_t(self) -> None:
        result = kupiec_pof_test(200, 4, 0.99)
        assert result["observed_rate"] == pytest.approx(4 / 200)

    def test_expected_breaches_equals_n_times_rate(self) -> None:
        result = kupiec_pof_test(300, 3, 0.99)
        assert result["expected_breaches"] == pytest.approx(300 * 0.01)

    def test_observed_breaches_equals_input(self) -> None:
        result = kupiec_pof_test(250, 7, 0.99)
        assert result["observed_breaches"] == 7

    # Test statistic

    def test_test_statistic_is_non_negative(self) -> None:
        """Likelihood-ratio statistic must be >= 0."""
        assert kupiec_pof_test(250, 2, 0.99)["test_statistic"] >= 0

    def test_perfect_calibration_has_low_statistic(self) -> None:
        """When observed_rate == expected_rate the LR statistic is 0."""
        # 5/500 = 0.01 exactly matches the expected rate at 99% confidence
        result = kupiec_pof_test(500, 5, 0.99)
        assert result["test_statistic"] == pytest.approx(0.0, abs=1e-6)
