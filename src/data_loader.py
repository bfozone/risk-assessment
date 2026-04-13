"""Data loading utilities for the risk assessment."""

import pandas as pd


def load_instruments(db_path: str = "data/reference.duckdb") -> pd.DataFrame:
    """
    Load instrument reference data from DuckDB.

    Returns a DataFrame with columns: instrument_id, instrument_name,
    asset_class, sub_class, sector, currency, country, credit_rating,
    maturity_date, coupon_rate, modified_duration
    """
    raise NotImplementedError("Implement this function")


def load_positions(db_path: str = "data/reference.duckdb") -> pd.DataFrame:
    """
    Load the **current** portfolio positions from DuckDB.

    The database contains a `positions_history` table with multiple snapshots
    over time (quarterly rebalances). Your job is to write SQL that returns
    only the most recent snapshot per instrument.

    Hint: a window function (ROW_NUMBER OVER PARTITION BY ...), DuckDB's
    QUALIFY clause, or a correlated subquery all work.

    You will likely want to JOIN with the `instruments` table so that
    downstream code (component VaR grouping, stress testing) has access
    to instrument metadata such as `sub_class`.

    Returns a DataFrame with at least the columns: portfolio_id,
    instrument_id, quantity, market_value_chf, weight, snapshot_date,
    sub_class
    """
    raise NotImplementedError("Implement this function")


def load_prices(parquet_path: str = "data/prices.parquet") -> pd.DataFrame:
    """
    Load price time series from parquet.

    Returns a DataFrame with columns: date, instrument_id, price.

    Note: the raw file contains data quality issues. Use `clean_prices()`
    before computing returns.
    """
    raise NotImplementedError("Implement this function")


def clean_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the raw price data.

    The raw prices.parquet contains a few deliberate quality issues that
    a production loader must handle:
      - Missing values (NaN prices for some dates)
      - Duplicate rows (same date + instrument with slightly different prices)
      - Outliers (clear fat-finger errors, e.g. a price 5x the surrounding values)

    Implement a cleaning strategy that produces a usable price series. Document
    your choices in the docstring or in REPORT.md.

    Returns a cleaned DataFrame with the same columns as the input.
    """
    raise NotImplementedError("Implement this function")


def load_scenarios(
    parquet_path: str = "data/scenarios.parquet",
) -> pd.DataFrame:
    """
    Load stress scenario definitions from parquet.

    Returns a DataFrame with columns: scenario_id, scenario_name,
    instrument_id, shock_return, description
    """
    raise NotImplementedError("Implement this function")
