"""Data loading utilities for the risk assessment pipeline.

HOW TO READ THIS FILE
---------------------
Each function does one job: load or clean one piece of data.
We use two data formats:
  - DuckDB  : a SQL database stored as a single file (like SQLite)
  - Parquet : a compressed binary file format (faster/smaller than CSV)

Key Python concept used everywhere: pd.DataFrame
  Think of it exactly like an Excel spreadsheet — rows and columns.
  pandas (imported as pd) is the library that gives us DataFrames.
"""

import numpy as np
import pandas as pd
import duckdb


# ─────────────────────────────────────────────
# 1. INSTRUMENTS
# ─────────────────────────────────────────────

def load_instruments(db_path: str = "data/reference.duckdb") -> pd.DataFrame:
    """Load instrument reference data from DuckDB.

    An "instrument" is just a security: a stock, a bond, etc.
    This table tells us metadata about each one (sector, currency, etc.).

    HOW DUCKDB WORKS:
      duckdb.connect() opens the file (read_only=True means we won't modify it).
      .execute(sql).df() runs SQL and returns a pandas DataFrame.

    Returns
    -------
    DataFrame with columns: instrument_id, instrument_name, asset_class,
    sub_class, sector, currency, country, credit_rating, maturity_date,
    coupon_rate, modified_duration
    """
    con = duckdb.connect(db_path, read_only=True)
    df = con.execute("SELECT * FROM instruments").df()
    con.close()
    return df


# ─────────────────────────────────────────────
# 2. POSITIONS  (current portfolio holdings)
# ─────────────────────────────────────────────

def load_positions(db_path: str = "data/reference.duckdb") -> pd.DataFrame:
    """Load the *current* portfolio positions from DuckDB.

    HOW THE DATA IS STRUCTURED:
      `positions_history` has multiple rows per instrument —
      one per quarterly rebalance (5 snapshots, so up to 5 rows per instrument).
      We only want the MOST RECENT snapshot.

    SQL TECHNIQUE — ROW_NUMBER() with QUALIFY:
      ROW_NUMBER() OVER (PARTITION BY instrument_id ORDER BY snapshot_date DESC)
        numbers rows newest-first within each instrument.
      QUALIFY = 1 keeps only the top row (most recent snapshot).
      This is equivalent to: "for each instrument, give me the latest row".

    We JOIN with `instruments` so downstream code has sub_class
    (needed for component VaR grouping and stress testing).

    Returns
    -------
    DataFrame with at least: portfolio_id, instrument_id, quantity,
    market_value_chf, weight, snapshot_date, sub_class
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
            i.asset_class,
            i.sector,
            i.currency
        FROM positions_history p
        JOIN instruments i USING (instrument_id)
        QUALIFY
            ROW_NUMBER() OVER (
                PARTITION BY p.instrument_id
                ORDER BY p.snapshot_date DESC
            ) = 1
    """
    con = duckdb.connect(db_path, read_only=True)
    df = con.execute(sql).df()
    con.close()
    return df


# ─────────────────────────────────────────────
# 3. RAW PRICES  (intentionally dirty!)
# ─────────────────────────────────────────────

def load_prices(parquet_path: str = "data/prices.parquet") -> pd.DataFrame:
    """Load raw price time series from a Parquet file.

    WHAT IS PARQUET?
      A binary file format optimised for columnar data.
      pandas reads it with pd.read_parquet().
      NOTE: This file has deliberate quality issues.
      Always call clean_prices() before using the data.

    The returned data is in *long* format:
        date       | instrument_id | price
        2024-01-02 | UBSG          | 25.30
        2024-01-02 | NESN          | 98.10
        ...

    Returns
    -------
    DataFrame with columns: date, instrument_id, price
    """
    df = pd.read_parquet(parquet_path)
    df["date"] = pd.to_datetime(df["date"])
    return df


# ─────────────────────────────────────────────
# 4. PRICE CLEANING  (the interesting part!)
# ─────────────────────────────────────────────

def clean_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Remove data quality issues from the raw price file.

    THREE PROBLEMS WE FIX, in order:

    PROBLEM 1 — Duplicate rows
      The same (date, instrument_id) pair appears twice with slightly
      different prices.
      Strategy: sort consistently, then drop_duplicates keeping the first row.

    PROBLEM 2 — Outliers (fat-finger errors)
      One instrument (UBSG) has a price ~5× its normal value on one day.
      Strategy: for each instrument, compute the median price across all days.
        Any price > 3× the median (or < 1/3 of it) is replaced with NaN.
      Why median not mean?  The median is not affected by the outlier itself,
        so it gives a stable reference. A mean would be dragged toward the outlier.

    PROBLEM 3 — Missing values (NaN)
      Some dates have no price for some instruments.
      Strategy: forward-fill (use the previous day's price), then back-fill
        (fill any remaining gaps at the start of the series).
      Financial industry standard: "no trade today = yesterday's price".

    Returns
    -------
    Cleaned DataFrame with the same columns as input, zero NaNs.
    """
    df = prices.copy()

    # ── Step 1: Sort so deduplication is deterministic ──────────────
    df = df.sort_values(["instrument_id", "date"]).reset_index(drop=True)

    # ── Step 2: Drop duplicate (date, instrument_id) rows ───────────
    df = df.drop_duplicates(subset=["date", "instrument_id"], keep="first")

    # ── Step 3: Replace outliers with NaN ───────────────────────────
    #   groupby("instrument_id")["price"].transform("median") computes
    #   each instrument's median and broadcasts it back to every row.
    #   So we can compare each price to its own instrument's median.
    medians = df.groupby("instrument_id")["price"].transform("median")
    outlier_mask = (df["price"] > 3 * medians) | (df["price"] < medians / 3)
    df.loc[outlier_mask, "price"] = np.nan

    # ── Step 4: Forward-fill then back-fill NaN per instrument ──────
    #   We must sort by date first so ffill goes forward in time.
    df = df.sort_values(["instrument_id", "date"])
    df["price"] = df.groupby("instrument_id")["price"].transform(
        lambda x: x.ffill().bfill()
    )

    # ── Step 5: Drop any remaining NaN rows (defensive) ─────────────
    df = df.dropna(subset=["price"])

    return df.reset_index(drop=True)


# ─────────────────────────────────────────────
# 5. STRESS SCENARIOS
# ─────────────────────────────────────────────

def load_scenarios(parquet_path: str = "data/scenarios.parquet") -> pd.DataFrame:
    """Load stress scenario definitions from Parquet.

    Each scenario defines a shock_return per instrument.
    Example: scenario "2008 Crisis" → UBSG: -0.35 (down 35%), NESN: -0.15 ...

    Returns
    -------
    DataFrame with columns: scenario_id, scenario_name,
    instrument_id, shock_return, description
    """
    return pd.read_parquet(parquet_path)
