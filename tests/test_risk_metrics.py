# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportMissingTypeStubs=false
"""Tests for risk metrics, data loading, and data cleaning.

Run from the project root:
    pytest tests/ -v
"""

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from src.backtest import run_rolling_backtest
from src.data_loader import clean_prices, load_positions, load_prices
from src.risk_metrics import (
    compute_component_var,
    compute_cvar_historical,
    compute_cvar_parametric,
    compute_var_historical,
    compute_var_parametric,
    kupiec_pof_test,
)
from src.stress import apply_scenarios

# ── Risk metric tests ───────────────────────────────────────────────

@pytest.fixture
def sample_returns() -> pd.Series:
    """Return deterministic N(0.0005, 0.01) returns for testing."""
    rng = np.random.default_rng(123)
    return pd.Series(rng.normal(0.0005, 0.01, 1000))


def test_var_historical_basic(sample_returns: pd.Series) -> None:
    """Historical VaR is positive and in a range for 1% vol."""
    var = compute_var_historical(sample_returns, confidence=0.99)
    assert var > 0
    assert 0.01 < var < 0.05


def test_cvar_exceeds_var(sample_returns: pd.Series) -> None:
    """Historical CVaR >= VaR at the same confidence."""
    var = compute_var_historical(sample_returns, confidence=0.99)
    cvar = compute_cvar_historical(sample_returns, confidence=0.99)
    assert cvar >= var


def test_var_parametric_basic(sample_returns: pd.Series) -> None:
    """Parametric VaR is positive and in a sane range for 1% vol."""
    var = compute_var_parametric(sample_returns, confidence=0.99)
    assert var > 0
    assert 0.01 < var < 0.05


def test_cvar_parametric_exceeds_var(sample_returns: pd.Series) -> None:
    """Parametric CVaR >= parametric VaR."""
    var = compute_var_parametric(sample_returns, confidence=0.99)
    cvar = compute_cvar_parametric(sample_returns, confidence=0.99)
    assert cvar >= var


def test_component_var_sums_to_total() -> None:
    """Component VaR contributions should sum approximately to total VaR."""
    rng = np.random.default_rng(123)
    dates = pd.bdate_range("2025-01-01", periods=200)

    returns_wide = pd.DataFrame(
        {
            "A": rng.normal(0, 0.01, 200),
            "B": rng.normal(0, 0.008, 200),
            "C": rng.normal(0, 0.006, 200),
        },
        index=dates,
    )

    positions = pd.DataFrame(
        {
            "instrument_id": ["A", "B", "C"],
            "weight": [0.4, 0.3, 0.3],
            "sub_class": ["EQ", "BOND", "BOND"],
        }
    )

    comp_var_df = compute_component_var(
        returns_wide,
        positions,
        confidence=0.99,
    )

    # Sum of component VaR contributions
    total_component_var = comp_var_df["component_var"].sum()

    # Compute total portfolio VaR (parametric)
    cov = returns_wide.cov().values
    weights = positions["weight"].values
    port_vol = float(np.sqrt(weights @ cov @ weights))
    total_var = port_vol * float(norm.ppf(0.99))

    # Allow small numerical tolerance
    assert abs(total_component_var - total_var) < 1e-4


def test_kupiec_known_cases() -> None:
    """Kupiec POF accepts 2/250 and rejects 10/250 at 99%."""
    result = kupiec_pof_test(250, 2, 0.99)
    assert not result["reject_95pct"]

    result2 = kupiec_pof_test(250, 10, 0.99)
    assert result2["reject_95pct"]


# ── Data loader / cleaning tests ────────────────────────────────────


def test_load_prices_returns_long_format() -> None:
    """Raw prices come back in long format with expected columns."""
    df = load_prices("data/prices.parquet")
    assert set(df.columns) == {"date", "instrument_id", "price"}
    assert len(df) > 0


def test_clean_prices_removes_nans() -> None:
    """clean_prices must strip NaN values from the raw file."""
    raw = load_prices("data/prices.parquet")
    assert raw["price"].isna().sum() > 0
    clean = clean_prices(raw)
    assert clean["price"].isna().sum() == 0


def test_clean_prices_removes_duplicates() -> None:
    """clean_prices must deduplicate (date, instrument_id) rows."""
    raw = load_prices("data/prices.parquet")
    clean = clean_prices(raw)
    dups = clean.duplicated(subset=["date", "instrument_id"]).sum()
    assert dups == 0


def test_clean_prices_removes_outliers() -> None:
    """The injected UBSG outlier (~5x normal) must be cleaned."""
    raw = load_prices("data/prices.parquet")
    clean = clean_prices(raw)
    ubsg = clean.loc[clean["instrument_id"] == "UBSG", "price"]
    assert float(ubsg.max()) < 60


def test_load_positions_returns_latest_snapshot() -> None:
    """One row per instrument, weights sum to 1."""
    pos = load_positions("data/reference.duckdb")
    assert len(pos) == 18
    assert pos["instrument_id"].is_unique
    assert abs(float(pos["weight"].sum()) - 1.0) < 1e-4


# ── Backtest tests ─────────────────────────────────────────────────


def test_rolling_backtest_detects_breach() -> None:
    """A large negative return after a calm window must be flagged as a breach."""
    dates = pd.bdate_range("2025-01-01", periods=65)
    calm = pd.Series(np.zeros(60), index=dates[:60])
    tail = pd.Series([0.001, 0.001, -0.10, 0.001, 0.001], index=dates[60:65])
    port_returns = pd.concat([calm, tail])

    result = run_rolling_backtest(port_returns, window=60, confidence=0.99)

    assert "backtest_df" in result
    assert "summary" in result

    backtest_df = result["backtest_df"]
    summary = result["summary"]

    assert len(backtest_df) == 5
    assert summary["n_obs"] == 5
    assert summary["n_breaches"] >= 1
    assert len(summary["breach_dates"]) >= 1
    assert "kupiec_test" in summary
    assert {"date", "realized_return", "var_threshold", "breach"}.issubset(backtest_df.columns)

# ── Stress testing tests ───────────────────────────────────────────

def test_apply_scenarios_basic() -> None:
    """Scenario P&L equals weight * shock sum across instruments."""
    positions = pd.DataFrame(
        {
            "instrument_id": ["A", "B"],
            "weight": [0.6, 0.4],
            "market_value_chf": [600_000.0, 400_000.0],
            "sub_class": ["EQ", "BOND"],
        }
    )

    scenarios = pd.DataFrame(
        {
            "scenario_id": ["S1", "S1"],
            "scenario_name": ["Crash", "Crash"],
            "instrument_id": ["A", "B"],
            "shock_return": [-0.10, 0.02],
            "description": ["Test crash", "Test crash"],
        }
    )

    result = apply_scenarios(positions, scenarios)

    assert len(result) == 1

    expected_return = 0.6 * (-0.10) + 0.4 * 0.02
    assert abs(float(result["portfolio_return"].iloc[0]) - expected_return) < 1e-8

    expected_pnl = 600_000 * (-0.10) + 400_000 * 0.02
    pnl_col = "portfolio_pnl_chf" if "portfolio_pnl_chf" in result.columns else "pnl_chf"
    assert abs(float(result[pnl_col].iloc[0]) - expected_pnl) < 1e-2