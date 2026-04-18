# `data_loader.py` — Design Decisions

Two sections of `data_loader.py` deserve explanation: the SQL query in `load_positions` and the three-step cleaning pipeline in `clean_prices`.

---

## 1. `load_positions` — Latest-snapshot query

```sql
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
```

```python
with duckdb.connect(db_path, read_only=True) as con:
    return con.execute(sql).fetchdf()
```

### Design decisions

**`positions_history` rather than a `positions` view**

The source table is an append-only history of daily snapshots. Querying it directly — rather than a pre-built `positions` view — keeps the loader self-contained and makes the filtering logic explicit and auditable.

**`QUALIFY ROW_NUMBER() OVER (...) = 1` — how it works**

The clause breaks into four distinct pieces that build on each other:

```text
QUALIFY   ROW_NUMBER()   OVER (PARTITION BY p.instrument_id ORDER BY p.snapshot_date DESC)   = 1
  │            │                           │                          │                        │
  │            │                           │                          │                        └─ keep only rank 1
  │            │                           │                          └─ rank 1 = most-recent date
  │            │                           └─ restart the counter for every instrument
  │            └─ assign an integer rank to each row within its group
  └─ filter on a window-function result (standard SQL cannot do this in WHERE)
```

**`ROW_NUMBER()`** assigns a unique integer to each row within the window frame,
starting at 1. It never ties — even if two rows share the same date they
receive different numbers (use `RANK()` instead if ties should both get rank 1,
but that would return multiple rows here).

**`OVER (...)`** defines the window — the set of rows each rank is computed
over. Without `OVER`, `ROW_NUMBER()` would be meaningless.

**`PARTITION BY p.instrument_id`** splits the table into independent groups,
one per instrument, and restarts the counter at 1 for each group. Without
this, DuckDB would rank all rows in the entire table together and `= 1` would
return only one row total.

**`ORDER BY p.snapshot_date DESC`** determines which row gets rank 1 within
each group. `DESC` puts the most-recent date first, so rank 1 is always the
latest snapshot. Changing to `ASC` would return the oldest snapshot instead.

**`= 1`** is the filter that discards every row except the top-ranked one per
group — i.e. the most-recent snapshot for each instrument.

**`QUALIFY`** is a DuckDB / BigQuery extension that applies this filter on the
window-function result *before* the final result set is returned. Standard SQL
cannot reference window functions in a `WHERE` clause (they are evaluated after
`WHERE`). The workaround without `QUALIFY` would be a subquery:

```sql
-- equivalent without QUALIFY (more verbose)
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY instrument_id ORDER BY snapshot_date DESC
    ) AS rn
    FROM positions_history
) ranked
WHERE rn = 1
```

`QUALIFY` compresses this into a single query level, making the intent
immediately readable.

#### Why this is better than the alternatives

| Alternative | Problem |
| --- | --- |
| `WHERE snapshot_date = (SELECT MAX(...))` | Scalar subquery returns one global maximum; silently drops any instrument whose last snapshot predates that maximum (stale instruments are lost) |
| `GROUP BY ... HAVING MAX(snapshot_date)` | `GROUP BY` collapses rows — you cannot `SELECT` non-aggregated columns like `quantity` or `weight` without also aggregating them |
| Python-side `.sort_values().groupby().last()` | Correct, but loads the entire history into memory before filtering; `QUALIFY` pushes the work into DuckDB so only the 18 final rows are transferred to Python |

`ROW_NUMBER() OVER (PARTITION BY instrument_id ORDER BY snapshot_date DESC) = 1`
tolerates instruments with different last-seen dates and scales to any number
of historical snapshots without changing the query.

**`JOIN instruments USING (instrument_id)` — single query, no Python merge**

Reference data (sub_class, currency, sector, etc.) is joined in SQL rather than loaded separately and merged in Python. This avoids the risk of a
mismatch in dtypes or index alignment between two DataFrames, and means the caller receives a single, fully-denormalised result ready for downstream use.

**`read_only=True`**

DuckDB acquires a write lock by default. Passing `read_only=True` prevents
accidental modification of the database and allows multiple processes to open
the file simultaneously (e.g. a notebook and the pipeline running in parallel).

**Context manager (`with duckdb.connect(...) as con`)**

The connection is closed immediately after the query returns. DuckDB holds an
OS-level file lock for the lifetime of the connection; releasing it promptly
avoids `IOException: database is locked` errors when other processes (e.g.
`bpython`, Jupyter) also need to read the file.

---

## 2. `clean_prices` — Three-step cleaning pipeline

### What it does

```python
# Step 1 — Deduplicate
df = (
    prices.groupby(["date", "instrument_id"], as_index=False)["price"]
    .mean()
    .sort_values(["instrument_id", "date"])
    .reset_index(drop=True)
)

# Step 2 — Outlier detection
rolling_med = df.groupby("instrument_id")["price"].transform(
    lambda s: s.rolling(window=5, center=True, min_periods=1).median()
)
ratio = df["price"] / rolling_med
df.loc[(ratio > 4) | (ratio < 0.25), "price"] = np.nan

# Step 3 — Fill
df["price"] = df.groupby("instrument_id")["price"].transform(
    lambda s: s.ffill().bfill()
)
```

### Step 1 — Deduplicate by averaging

When multiple rows share the same `(date, instrument_id)` key they are collapsed to their mean. Taking the mean is preferred over `first` or `last` because neither duplicate row is considered more authoritative; the mean minimises the perturbation to surrounding prices.

**Why deduplication precedes outlier detection**

The rolling median in Step 2 is a 5-*day* window. If duplicates are still present, two observations fall on the same date and the window no longer represents 5 distinct trading days — the median is skewed. Deduplicating first ensures the outlier detector always operates on a clean, single-row-per-date series with a well-defined rolling window.

The edge case where one duplicate is a fat-finger (e.g. 100 and 600) is handled correctly: the mean (350) lies well outside the 4× threshold relative to the surrounding ~100 prices and is subsequently replaced with NaN in Step 2.

### Step 2 — Outlier detection via rolling median ratio

A price is flagged as an outlier if it deviates by more than **4×** above or **0.25×** below the local rolling median:

```python
ratio = price / rolling_median(window=5, centered)
outlier  if  ratio > 4  or  ratio < 0.25
```

Price series are non-stationary: the absolute level drifts over time, so a fixed z-score threshold would fire on genuine trends. A ratio to the local median is scale-invariant and captures fat-finger errors (e.g. a decimal-point shift that makes a price 10× too large) regardless of the instrument's price
level.

**Why `window=5, center=True`**

- A centred window uses up to 2 days before and 2 days after the candidate
  price. This makes the reference median symmetric around the suspect point,
  which is more robust than a trailing window that can be dragged up by a
  prior outlier.
- Window=5 is wide enough to produce a stable median for typical daily price
  series while remaining sensitive to single-day spikes.
- `min_periods=1` prevents the window from returning NaN at the edges of the
  series (first and last two observations), where a full 5-day window is not
  available.

Converting outliers to NaN unifies them with genuine missing values. Both
are then handled by the same forward/back-fill logic in Step 3, avoiding
duplicate imputation code paths.

### Step 3 — Forward-fill then back-fill

```python
s.ffill().bfill()
```

- **Forward-fill** (`ffill`) propagates the last known good price forward. This is the standard convention for financial time series: if no trade or quote is observed, yesterday's close is carried forward (stale price).
- **Back-fill** (`bfill`) handles leading NaNs that `ffill` cannot resolve (there is no prior observation to carry forward). Back-filling from the first real price is the least-bad choice for an instrument whose history starts   with missing data.

Both fills are applied **per instrument** (`groupby("instrument_id")`) so that
prices from one instrument never contaminate another.

### Immutability

The function operates on an internal copy (`groupby(...).mean()` returns a new
DataFrame); the caller's original `prices` DataFrame is never modified. This
is verified explicitly by `TestCleanPrices::test_input_dataframe_not_mutated`.
