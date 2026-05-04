
import numpy as np
import pandas as pd
import duckdb


def load_instruments(db_path: str = "data/reference.duckdb") -> pd.DataFrame:
    """
    Load instrument reference data from DuckDB.

    Returns a DataFrame with columns: instrument_id, instrument_name,
    asset_class, sub_class, sector, currency, country, credit_rating,
    maturity_date, coupon_rate, modified_duration
    """
    con = duckdb.connect(db_path, read_only=True)
    df = con.execute("SELECT * FROM instruments").df()
    con.close()
    return df


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


def load_prices(parquet_path: str = "data/prices.parquet") -> pd.DataFrame:
    """
    Load price time series from parquet.

    Returns a DataFrame with columns: date, instrument_id, price.

    Note: the raw file contains data quality issues. Use `clean_prices()`
    before computing returns.
    """
    df = pd.read_parquet(parquet_path)
    df["date"] = pd.to_datetime(df["date"])
    return df



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

    # 1. Sort and prep the data
    prices = prices.sort_values(["instrument_id", "date"]).reset_index(drop=True)
    
    # A. Duplicate rows are removed by keeping the first occurrence.
    prices = prices.drop_duplicates(subset=["instrument_id", "date"], keep="first")

    # B. Missing values are filled with the previous day's price
    prices["price"] = prices.groupby("instrument_id")["price"].ffill()
    
    # C. Outliers are replaced with the previous valid price

    # Calculate the rolling median of the PREVIOUS 5 days (using .shift(1))
    rolling_medians = prices.groupby("instrument_id")["price"].transform(
        lambda x: x.rolling(window=5, min_periods=1).median().shift(1)
    )
    
    # Define the Outlier condition
    # Example: Outlier if the price is > 3x the median, or < 1/3 of the median
    outlier_mask = (prices["price"] > 3 * rolling_medians) | (prices["price"] < rolling_medians / 3)
    
    # The first day has no history (rolling median is NaN), so it cannot be an outlier
    outlier_mask = outlier_mask.fillna(False)
    
    # 4. Erase outliers and replace them with the previous valid price
    prices.loc[outlier_mask, "price"] = np.nan
    prices["price"] = prices.groupby("instrument_id")["price"].ffill()
    
    # 5. Housekeeping
    prices = prices.dropna(subset=["price"]).reset_index(drop=True)
    
    return prices



def load_scenarios(parquet_path: str = "data/scenarios.parquet") -> pd.DataFrame:
    """
    Load stress scenario definitions from parquet.

    Returns a DataFrame with columns: scenario_id, scenario_name,
    instrument_id, shock_return, description
    """
    return pd.read_parquet(parquet_path)
