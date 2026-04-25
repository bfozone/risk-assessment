"""Data ingestion and cleaning layer code for the Risk Assessment."""

import duckdb
import numpy as np
import pandas as pd

# Below the five functions in this file. The functions return a df dataframe which is then used in the next steps.

# Loading of instruments and position history - metadata for each instrument

# The function returns instruments reference data from the DuckDB file.

def load_instruments(db_path: str = "data/reference.duckdb") -> pd.DataFrame:
    """
    Load instrument reference data from DuckDB.

    Returns a DataFrame with columns: instrument_id, instrument_name,
    asset_class, sub_class, sector, currency, country, credit_rating,
    maturity_date, coupon_rate, modified_duration
    """
    query = """
    SELECT
        instrument_id,
        instrument_name,
        asset_class,
        sub_class,
        sector,
        currency,
        country,
        credit_rating,
        maturity_date,
        coupon_rate,
        modified_duration
    FROM instruments
    ORDER BY instrument_id
    """
    with duckdb.connect(db_path, read_only=True) as con:
        df = con.execute(query).df()

    if "maturity_date" in df.columns:
        df["maturity_date"] = pd.to_datetime(df["maturity_date"], errors="coerce")

    return df

    """raise NotImplementedError("Implement this function")"""

# This function returns the current portfolio positions from the DuckDB file and the SQL code to get the most recent snapshot

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
    query = """
    SELECT
        p.portfolio_id,
        p.instrument_id,
        p.quantity,
        p.market_value_chf,
        p.weight,
        p.snapshot_date,
        i.instrument_name,
        i.asset_class,
        i.sub_class,
        i.currency,
        i.country,
        i.modified_duration
    FROM positions_history p
    INNER JOIN instruments i
        ON p.instrument_id = i.instrument_id
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY p.portfolio_id, p.instrument_id
        ORDER BY p.snapshot_date DESC
    ) = 1
    ORDER BY p.instrument_id
    """
    with duckdb.connect(db_path, read_only=True) as con:
        df = con.execute(query).df()

    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], errors="coerce")
    return df

    

# The function loads historical prices from parquet file
def load_prices(parquet_path: str = "data/prices.parquet") -> pd.DataFrame:
    """
    Load price time series from parquet.

    Returns a DataFrame with columns: date, instrument_id, price.

    Note: the raw file contains data quality issues. Use `clean_prices()`
    before computing returns.
    """
    df = pd.read_parquet(parquet_path)

    required = {"date", "instrument_id", "price"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in prices parquet: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    return df
    

# The function clean_prices performs all the data preprocessing steps before simple returns are calculated in the returns.py file.
# The approach below aims to spot and then remediate potential data quality issues which might lead to misleading risk metrics.

def clean_prices(prices: pd.DataFrame) -> pd.DataFrame:


    # This is a simple required column check
    required = {"date", "instrument_id", "price"}
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"Input prices missing columns: {sorted(missing)}")

    df = prices.copy()

    # Standardize types - date column in datetime format and price in numeric format
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    # Drop rows with missing structural keys - here it is necessary as these are structural identifiers. Prices are tackled below.
    df = df.dropna(subset=["date", "instrument_id"])

    # Collapse duplicates - it averages the prices into one row. 
    df = (
        df.groupby(["date", "instrument_id"], as_index=False)["price"]
        .mean()
    )

    # Sort for time-series processing - this step is necessary before I calculate the simple returns to spot outliers, etc..
    df = df.sort_values(["instrument_id", "date"]).reset_index(drop=True)

    # The funnction below is at instrument-level so that I can efficiently remediate any potential outlier or missing price

    def _clean_one_instrument(group: pd.DataFrame) -> pd.DataFrame:
        group = group.sort_values("date").copy()

        # Compute daily returns
        ret = group["price"].pct_change()

        # Flag obvious cases where the one-day return is above +/-30% - the identified cases are marked as missing values
        threshold = 0.30
        group.loc[ret.abs() > threshold, "price"] = np.nan

        # Fill missing values within instrument - ffill takes the previous valid price for missing values. Next valid price is taken if missing happens at the start.
        group["price"] = group["price"].ffill().bfill()

        return group

    # Avoid fragile group by-apply index behavior which I have encountered 

    cleaned_groups = []
    for _, group in df.groupby("instrument_id", sort=False):
        cleaned_groups.append(_clean_one_instrument(group))

    # This function recombines all the instruments into one df

    df = pd.concat(cleaned_groups, ignore_index=True)

    # Final validation
    if df["price"].isna().any():
        raise ValueError("Unresolved NaN prices remain after cleaning.")

    return df[["date", "instrument_id", "price"]]


# The function loads the scenarios from parquet file
def load_scenarios(
    parquet_path: str = "data/scenarios.parquet",
) -> pd.DataFrame:
    df = pd.read_parquet(parquet_path)

    required = {
        "scenario_id",
        "scenario_name",
        "instrument_id",
        "shock_return",
        "description",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in scenarios parquet: {sorted(missing)}")
    
    # Shock returns to numeric format.
    df["shock_return"] = pd.to_numeric(df["shock_return"], errors="coerce")
    return df

    
