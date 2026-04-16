# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false
"""Tests for src/data_loader.py.

Tests are organised into one class per public function:
  - TestCleanPrices   — unit tests using synthetic DataFrames (no I/O)
  - TestLoadInstruments, TestLoadPositions, TestLoadPrices, TestLoadScenarios
                      — integration tests against the real data/ files

Integration fixtures use scope="module" so each file is read once per
test session rather than once per test function.
"""

import numpy as np
import pandas as pd
import pytest

from data_loader import (
    clean_prices,
    load_instruments,
    load_positions,
    load_prices,
    load_scenarios,
)

# ---------------------------------------------------------------------------
# Private constants
# ---------------------------------------------------------------------------

_DB_PATH = "data/reference.duckdb"
_PRICES_PATH = "data/prices.parquet"
_SCENARIOS_PATH = "data/scenarios.parquet"

_INSTRUMENT_COLUMNS: list[str] = [
    "instrument_id",
    "instrument_name",
    "asset_class",
    "sub_class",
    "sector",
    "currency",
    "country",
    "credit_rating",
    "maturity_date",
    "coupon_rate",
    "modified_duration",
]

# Columns that must never be null (nullable fields like sector/rating excluded).
_INSTRUMENT_REQUIRED_COLUMNS: list[str] = [
    "instrument_id",
    "instrument_name",
    "asset_class",
    "sub_class",
    "currency",
    "country",
]

_POSITION_REQUIRED_COLUMNS: list[str] = [
    "portfolio_id",
    "instrument_id",
    "quantity",
    "market_value_chf",
    "weight",
    "snapshot_date",
    "sub_class",
]

_SCENARIO_COLUMNS: list[str] = [
    "scenario_id",
    "scenario_name",
    "instrument_id",
    "shock_return",
    "description",
]

# ---------------------------------------------------------------------------
# Integration fixtures — loaded once per module session
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def instruments() -> pd.DataFrame:
    return load_instruments(_DB_PATH)


@pytest.fixture(scope="module")
def positions() -> pd.DataFrame:
    return load_positions(_DB_PATH)


@pytest.fixture(scope="module")
def raw_prices() -> pd.DataFrame:
    return load_prices(_PRICES_PATH)


@pytest.fixture(scope="module")
def scenarios() -> pd.DataFrame:
    return load_scenarios(_SCENARIOS_PATH)


# ---------------------------------------------------------------------------
# Synthetic fixtures — cheap, function-scoped
# ---------------------------------------------------------------------------


@pytest.fixture
def prices_with_nans() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=6)
    return pd.DataFrame(
        {
            "date": dates,
            "instrument_id": ["A"] * 6,
            "price": [100.0, np.nan, 102.0, np.nan, 104.0, 105.0],
        }
    )


@pytest.fixture
def prices_with_leading_nans() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=4)
    return pd.DataFrame(
        {
            "date": dates,
            "instrument_id": ["A"] * 4,
            "price": [np.nan, np.nan, 100.0, 101.0],
        }
    )


@pytest.fixture
def prices_already_clean() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=10)
    return pd.DataFrame(
        {
            "date": dates,
            "instrument_id": ["A"] * 10,
            "price": [100.0 + i for i in range(10)],
        }
    )


@pytest.fixture
def prices_with_duplicates() -> pd.DataFrame:
    """Two rows for 2024-01-01 with slightly different prices (100 and 102)."""
    dates = pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-03"])
    return pd.DataFrame(
        {
            "date": dates,
            "instrument_id": ["A", "A", "A", "A"],
            "price": [100.0, 102.0, 103.0, 104.0],
        }
    )


@pytest.fixture
def prices_with_outlier() -> pd.DataFrame:
    """Ten rows for instrument X; index 5 is a 6x fat-finger (620 vs ~100)."""
    dates = pd.date_range("2024-01-01", periods=10)
    prices = [100.0] * 10
    prices[5] = 620.0
    return pd.DataFrame({"date": dates, "instrument_id": ["X"] * 10, "price": prices})


@pytest.fixture
def prices_multi_instrument() -> pd.DataFrame:
    """Instrument A has a NaN; instrument B has a 6x outlier (1200 vs ~200)."""
    n = 10
    dates = pd.date_range("2024-01-01", periods=n)
    prices_a = [50.0] * n
    prices_a[1] = np.nan  # mid-series NaN
    prices_b = [200.0] * n
    prices_b[4] = 1200.0  # 6x fat-finger outlier
    return pd.DataFrame(
        {
            "date": list(dates) * 2,
            "instrument_id": ["A"] * n + ["B"] * n,
            "price": prices_a + prices_b,
        }
    )


# ---------------------------------------------------------------------------
# TestCleanPrices
# ---------------------------------------------------------------------------


class TestCleanPrices:
    """Unit tests for clean_prices using synthetic DataFrames."""

    # NaN handling

    def test_leading_nans_backfilled(self, prices_with_leading_nans: pd.DataFrame) -> None:
        result = clean_prices(prices_with_leading_nans)
        assert result["price"].isna().sum() == 0
        # Back-fill propagates the first real value (100.0) to the leading NaNs.
        assert result["price"].iloc[0] == pytest.approx(100.0)

    def test_already_clean_data_is_unchanged(self, prices_already_clean: pd.DataFrame) -> None:
        result = clean_prices(prices_already_clean)
        pd.testing.assert_series_equal(
            result["price"].reset_index(drop=True),
            prices_already_clean["price"].reset_index(drop=True),
        )

    # Duplicate handling

    def test_duplicate_prices_averaged(self, prices_with_duplicates: pd.DataFrame) -> None:
        """Duplicate rows for the same date are resolved by taking the mean."""
        result = clean_prices(prices_with_duplicates)
        jan1_price = result.loc[result["date"] == pd.Timestamp("2024-01-01"), "price"]
        assert float(jan1_price.iloc[0]) == pytest.approx(101.0)  # mean(100, 102)

    # Outlier handling

    def test_all_prices_positive_after_cleaning(self, prices_with_outlier: pd.DataFrame) -> None:
        assert (clean_prices(prices_with_outlier)["price"] > 0).all()

    # Multi-instrument isolation

    def test_multi_instrument_no_nans(self, prices_multi_instrument: pd.DataFrame) -> None:
        assert clean_prices(prices_multi_instrument)["price"].isna().sum() == 0

    def test_outlier_cleaning_isolated_per_instrument(
        self, prices_multi_instrument: pd.DataFrame
    ) -> None:
        """Cleaning instrument B's outlier must not shift instrument A's prices."""
        result = clean_prices(prices_multi_instrument)
        assert float(result.loc[result["instrument_id"] == "A", "price"].max()) < 100.0
        assert float(result.loc[result["instrument_id"] == "B", "price"].max()) < 500.0

    # Immutability

    def test_input_dataframe_not_mutated(self, prices_with_nans: pd.DataFrame) -> None:
        original = prices_with_nans["price"].copy()
        clean_prices(prices_with_nans)
        pd.testing.assert_series_equal(prices_with_nans["price"], original)


# ---------------------------------------------------------------------------
# TestLoadInstruments
# ---------------------------------------------------------------------------


class TestLoadInstruments:
    """Integration tests for load_instruments."""

    def test_exact_columns_returned(self, instruments: pd.DataFrame) -> None:
        assert list(instruments.columns) == _INSTRUMENT_COLUMNS

    def test_non_empty(self, instruments: pd.DataFrame) -> None:
        assert len(instruments) > 0

    def test_instrument_ids_unique(self, instruments: pd.DataFrame) -> None:
        assert instruments["instrument_id"].is_unique

    @pytest.mark.parametrize("col", _INSTRUMENT_REQUIRED_COLUMNS)
    def test_required_column_has_no_nulls(self, instruments: pd.DataFrame, col: str) -> None:
        assert instruments[col].notna().all()


# ---------------------------------------------------------------------------
# TestLoadPositions
# ---------------------------------------------------------------------------


class TestLoadPositions:
    """Integration tests for load_positions."""

    @pytest.mark.parametrize("col", _POSITION_REQUIRED_COLUMNS)
    def test_required_column_present(self, positions: pd.DataFrame, col: str) -> None:
        assert col in positions.columns

    def test_non_empty(self, positions: pd.DataFrame) -> None:
        assert len(positions) > 0

    def test_single_snapshot_date(self, positions: pd.DataFrame) -> None:
        """All rows must share the same date — only the latest snapshot is returned."""
        assert positions["snapshot_date"].nunique() == 1

    def test_sub_class_fully_populated(self, positions: pd.DataFrame) -> None:
        assert positions["sub_class"].notna().all()


# ---------------------------------------------------------------------------
# TestLoadPrices
# ---------------------------------------------------------------------------


class TestLoadPrices:
    """Integration tests for load_prices."""

    def test_raw_file_contains_duplicates(self, raw_prices: pd.DataFrame) -> None:
        """Asserts the quality issue that clean_prices is expected to resolve."""
        assert raw_prices.duplicated(subset=["date", "instrument_id"]).any()


# ---------------------------------------------------------------------------
# TestLoadScenarios
# ---------------------------------------------------------------------------


class TestLoadScenarios:
    """Integration tests for load_scenarios."""

    @pytest.mark.parametrize("col", _SCENARIO_COLUMNS)
    def test_required_column_present(self, scenarios: pd.DataFrame, col: str) -> None:
        assert col in scenarios.columns

    def test_non_empty(self, scenarios: pd.DataFrame) -> None:
        assert len(scenarios) > 0

    def test_multiple_distinct_scenarios(self, scenarios: pd.DataFrame) -> None:
        assert scenarios["scenario_id"].nunique() >= 2

    def test_shock_returns_are_finite(self, scenarios: pd.DataFrame) -> None:
        assert np.isfinite(scenarios["shock_return"]).all()
