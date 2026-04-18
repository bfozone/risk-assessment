"""Data loading utilities for the risk assessment."""

import duckdb
import numpy as np
import pandas as pd


def load_instruments(db_path: str = "data/reference.duckdb") -> pd.DataFrame:
    """
    Load instrument reference data from DuckDB.

    Returns a DataFrame with columns: instrument_id, instrument_name,
    asset_class, sub_class, sector, currency, country, credit_rating,
    maturity_date, coupon_rate, modified_duration
    """
    with duckdb.connect(db_path, read_only=True) as con:
        return con.execute("SELECT * FROM instruments").fetchdf()


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
    sql = """
        SELECT
            p.portfolio_id,
            p.instrument_id,
            p.quantity,
            p.market_value_chf,
            p.weight,
            p.snapshot_date,
            i.sub_class,
            i.instrument_name,
            i.asset_class,
            i.sector,
            i.currency,
            i.country,
            i.credit_rating,
            i.maturity_date,
            i.coupon_rate,
            i.modified_duration
        FROM positions_history p
        JOIN instruments i USING (instrument_id)
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY p.instrument_id
            ORDER BY p.snapshot_date DESC
        ) = 1
    """
    with duckdb.connect(db_path, read_only=True) as con:
        return con.execute(sql).fetchdf()


def load_prices(parquet_path: str = "data/prices.parquet") -> pd.DataFrame:
    """
    Load price time series from parquet.

    Returns a DataFrame with columns: date, instrument_id, price.

    Note: the raw file contains data quality issues. Use `clean_prices()`
    before computing returns.
    """
    return pd.read_parquet(parquet_path)


def clean_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the raw price data.

    The raw prices.parquet contains a few deliberate quality issues that
    a production loader must handle:
      - Missing values (NaN prices for some dates)
      - Duplicate rows (same date + instrument with slightly different prices)
      - Outliers (clear fat-finger errors, e.g. a price 5x the surrounding values)

    Cleaning strategy:
      1. Duplicates: for the same (date, instrument_id) pair, average the prices.
         Averaging is preferred over keeping first/last because neither duplicate
         is clearly authoritative; the mean minimises the perturbation.
      2. Outliers: within each instrument's time series, flag any price whose
         ratio to the rolling 5-day median exceeds 4x (or is below 0.25x).
         Flagged values are replaced with NaN so they are treated identically
         to genuine missing values in step 3.
      3. Missing values (original NaNs + outlier-replaced NaNs): forward-fill
         within each instrument, then back-fill to handle leading NaNs.

    Returns a cleaned DataFrame with the same columns as the input.
    """
    df = (
        prices.groupby(["date", "instrument_id"], as_index=False)
        .agg({"price": "mean"})
        .sort_values(by=["instrument_id", "date"])
        .reset_index(drop=True)
    )

    # Detect outliers: prices more than 4x or less than 0.25x the local rolling median.
    rolling_med = df.groupby("instrument_id")["price"].transform(
        lambda s: s.rolling(window=5, center=True, min_periods=1).median()
    )
    ratio = df["price"] / rolling_med
    df.loc[(ratio > 4) | (ratio < 0.25), "price"] = np.nan

    df["price"] = df.groupby("instrument_id")["price"].transform(lambda s: s.ffill().bfill())

    return df


def load_scenarios(
    parquet_path: str = "data/scenarios.parquet",
) -> pd.DataFrame:
    """
    Load stress scenario definitions from parquet.

    Returns a DataFrame with columns: scenario_id, scenario_name,
    instrument_id, shock_return, description
    """
    return pd.read_parquet(parquet_path)
