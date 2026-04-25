"""Return generation code for the Risk Assessment."""

import pandas as pd

# The functions below are preparing the stage for the risk metrics calculation step, in particular the cleaned long-format prices are reshaped into a matrix,  instrument simple returns computed ,and a single portfolio return series is obtained per aggregation

# Sequence is: cleaned prices >> wide price matrix (i.e., date column and then each instrument header is a column with the respective price series)>> return matrix >> weighted portfolio return series.

def build_prices_wide(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Convert long-format cleaned prices into a wide price matrix.

    Input columns required:
    - date
    - instrument_id
    - price

    Returns:
        DataFrame with:
        - index = date
        - columns = instrument_id
        - values = price
    """
    required = {"date", "instrument_id", "price"}
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"Input prices missing columns: {sorted(missing)}")

    df = prices.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["date", "instrument_id", "price"])

    prices_wide = (
        df.pivot(index="date", columns="instrument_id", values="price")
        .sort_index()
        .sort_index(axis=1)
    )

    return prices_wide

# This function is key as it produces the input for portfolio return, VaR/ES, backtesting, etc..
def build_returns_wide(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Build instrument-level returns in wide format from cleaned prices.

    Input:
        long-format cleaned prices with columns:
        - date
        - instrument_id
        - price

    Returns:
        DataFrame with:
        - index = date
        - columns = instrument_id
        - values = simple returns
    """
    prices_wide = build_prices_wide(prices)
    returns_wide = prices_wide.pct_change()

    # Drop the first row because pct_change creates NaN there
    returns_wide = returns_wide.dropna(how="all")

    return returns_wide


def compute_portfolio_returns(
    returns_wide: pd.DataFrame,
    positions: pd.DataFrame,
    weight_col: str = "weight",
) -> pd.Series:
    """
    Compute portfolio returns as weighted sum of instrument returns.

    Assumes:
    - returns_wide columns are instrument_id
    - positions contains instrument_id and weight

    Returns:
        pd.Series of portfolio returns indexed by date
    """
    required = {"instrument_id", weight_col}
    missing = required - set(positions.columns)
    if missing:
        raise ValueError(f"Positions missing columns: {sorted(missing)}")

    if returns_wide.empty:
        raise ValueError("returns_wide is empty.")

    pos = positions[["instrument_id", weight_col]].copy()
    pos = pos[pos["instrument_id"].isin(returns_wide.columns)]

    if pos.empty:
        raise ValueError("No overlapping instrument_id values between returns and positions.")

    weights = (
        pos.drop_duplicates(subset=["instrument_id"])
        .set_index("instrument_id")[weight_col]
        .reindex(returns_wide.columns)
        .fillna(0.0)
    )

    total_weight = weights.sum()
    if total_weight == 0:
        raise ValueError("Sum of portfolio weights is zero.")

    # Optional normalization in case weights do not sum exactly to 1
    weights = weights / total_weight

    portfolio_returns = returns_wide.mul(weights, axis=1).sum(axis=1)
    portfolio_returns.name = "portfolio_return"

    return portfolio_returns