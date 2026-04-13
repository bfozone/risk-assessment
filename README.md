# Investment Risk Assessment

## Scenario

You are joining the Investment Risk team at an asset management firm. The team operates an internal risk analytics platform that processes daily risk metrics for the firm's investment portfolios.

You have been asked to build a **containerized risk analysis pipeline** for the firm's flagship **multi-asset fund** (CHF 500M, Swiss and European equities and bonds). The pipeline loads the portfolio data, computes risk metrics, runs a VaR backtest, applies stress scenarios, and writes the results to disk as JSON/CSV files and PNG plots.

The pipeline must run inside a Docker container orchestrated via `docker compose`. This mirrors how our production risk jobs are deployed.

The CRO and the hiring manager will review your work in the second interview.

## Scope and pace

There is no time limit and we do not time your work. Please note in `REPORT.md` roughly how long you spent and what you chose to prioritize. That context helps us calibrate and is never used to penalize you.

The assessment splits deliverables into **core** (required) and **stretch** (optional). A clean, well-tested core beats an everything-half-done submission. Use stretch items to show us what you care about, not as a checklist.

**Core (required):**

- All 5 functions in `src/data_loader.py`, including a defensible `clean_prices`
- All 6 functions in `src/risk_metrics.py`
- `run_rolling_backtest` in `src/backtest.py`
- `apply_scenarios` in `src/stress.py` (the 3 predefined scenarios)
- Core output files (see [Required outputs](#required-outputs-in-output))
- A working `Dockerfile` and `docker-compose.yml` so that `docker compose up --build` populates `./output/` on the host
- The provided `pytest` suite passing (the tests only cover core functions, not stretch)
- `REPORT.md` sections: executive summary, method comparison, backtest findings, production architecture

**Stretch (pick what you want to show us):**

- Stretch output files (see [Required outputs](#required-outputs-in-output))
- Own tests beyond the provided ones
- Benchmark-relative risk (tracking error, active risk decomposition vs the benchmark in `portfolio_meta`)
- Extended methodology (EWMA-weighted VaR, Christoffersen conditional coverage, ES backtest, filtered historical simulation)
- Container polish (non-root user, separate test service, multi-stage build)

If you skip a stretch item, say so in `REPORT.md` and tell us what you would do with more time. We value honest prioritization more than false completeness.

## Interview follow-up

After we review your submission, we invite you to a **follow-up interview** to:

1. **Present your work** (15 to 20 minutes): walk us through the pipeline and your design decisions, and highlight anything you would change with more time
2. **Answer questions** on the risk methodology, your code, your Dockerfile, and the architecture sketch
3. **Discuss extensions**: what would you add if this were going into production? What are the main limitations of what you built?

Be ready to share your screen and walk through the code live. How you reason about your choices matters as much as the code itself.

## Use of AI coding assistants

You may use any tools you would normally use at work: AI assistants (Claude, ChatGPT, Copilot, Cursor), library documentation, Stack Overflow. We use these tools ourselves.

**You own what you submit.** Every function, every decision, and every claim in your `REPORT.md` must be something you can defend. In the interview we walk through specific functions, ask why you made certain trade-offs, and discuss alternatives. "I pasted the prompt and it worked" does not fly.

- **Fine:** using an LLM to recall the parametric CVaR formula, debug a pandas pivot, or scaffold a Dockerfile you then adapt.
- **Fine:** using an LLM to draft the architecture section of `REPORT.md`, if you can defend every claim in it.
- **Not fine:** submitting code or writing you cannot explain, or that does things you did not intend. Iterating on prompts until something runs without understanding the output ("vibe coding") shows up quickly in the interview.

Feel free to note in `REPORT.md` where you leaned on AI and where you did not. Optional but appreciated.

## Getting started

### 1. Clone the repo and create your branch

Accept the GitHub invitation you received by email, then:

```bash
git clone git@github.com:<org>/bam-risk-assessment.git
cd bam-risk-assessment

# Create your own working branch
git checkout -b candidate/<your-firstname-lastname>
# e.g. git checkout -b candidate/jane-doe
```

All of your work must happen on this branch. Do not push directly to `main`.

### 2. (optional) Set up a local Python environment

Useful if you want to iterate on the risk logic outside of Docker:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
python setup_check.py

# Run the pipeline locally
python run_analysis.py

# Run the tests
pytest tests/ -v
```

The final deliverable must run in Docker. Verify `docker compose up --build` works end-to-end before pushing.

## How we will evaluate your work

Once you have pushed your branch, we:

1. `git fetch` and `git checkout candidate/<your-name>`
2. Run `docker compose up --build` and check that output files appear in `./output/`
3. Run the tests inside the container
4. Read your `REPORT.md` and inspect the generated outputs
5. Review your code **and your commit history**

## Repository layout

```text
bam-risk-assessment/
├── Dockerfile                  # YOU complete this
├── docker-compose.yml          # YOU complete this
├── .dockerignore
├── README.md                   # this file
├── REPORT.md                   # YOU write your findings here
├── pyproject.toml              # project metadata
├── requirements.txt            # Python dependencies
├── setup_check.py              # local env verification
├── run_analysis.py             # entry point, YOU complete this
├── data/                       # input data (read this, don't modify)
│   ├── reference.duckdb
│   ├── prices.parquet
│   └── scenarios.parquet
├── src/                        # YOU implement these
│   ├── data_loader.py          # DuckDB + parquet loading + clean_prices
│   ├── risk_metrics.py         # VaR, CVaR, component VaR, Kupiec test
│   ├── backtest.py             # rolling VaR backtest
│   ├── stress.py               # scenario application
│   └── reporting.py            # JSON/CSV/PNG output writers
├── tests/
│   └── test_risk_metrics.py    # tests that your implementations must pass
└── output/                     # pipeline output lands here (mounted volume)
```

## Data description

The portfolio data reflects a typical production setup: reference data in a database, time series in columnar files.

### `data/reference.duckdb`: DuckDB database

| Table | Description |
| ------- | ------------- |
| `instruments` | 18 rows. Metadata per instrument: asset class, sector, duration, rating, etc. |
| `positions_history` | 90 rows. Portfolio holdings across **5 quarterly snapshots** (the fund rebalances). You must extract the **latest snapshot** per instrument with SQL. |
| `portfolio_meta` | 1 row. Fund-level metadata: NAV, currency, benchmark, dates. |

You can explore the schema with:

```python
import duckdb
con = duckdb.connect("data/reference.duckdb", read_only=True)
con.sql("SHOW TABLES").show()
con.sql("DESCRIBE instruments").show()
```

### `data/prices.parquet`: long format

Columns: `date`, `instrument_id`, `price`. About 1 year of daily business-day prices for all 18 instruments. You will need to pivot this to wide format for return calculations.

**The raw file contains deliberate data quality issues** (missing values, a duplicate row, an outlier). You must implement a `clean_prices()` function that handles them before computing returns. Document your cleaning strategy.

### `data/scenarios.parquet`: long format

Columns: `scenario_id`, `scenario_name`, `instrument_id`, `shock_return`, `description`. Three predefined stress scenarios, each with per-instrument shocks expressed as returns (e.g., `-0.15` = -15%).

## Required outputs in `output/`

**Core (required):**

| File | Content |
| ------ | --------- |
| `risk_metrics.json` | Historical and parametric VaR/CVaR at 95% and 99%; component VaR by sub_class |
| `backtest.json` | Breach dates, counts, expected breaches, Kupiec test result |
| `scenarios.csv` | Stress scenario results with P&L per scenario |

**Stretch (optional):**

| File | Content |
| ------ | --------- |
| `backtest.png` | Rolling VaR backtest plot: returns + VaR threshold + breach markers |
| `correlation_heatmap.png` | Correlation matrix of instrument returns |
| `summary.txt` | Human-readable plain-text summary |

The exact schema is up to you. What matters is content and clarity.

## Tasks in detail

The sections below are the technical spec for each piece of the pipeline. See **Scope and pace** above for which parts are core vs stretch.

### 1. Data loading and cleaning

Implement the five functions in `src/data_loader.py`:

- `load_instruments`: simple `SELECT` from DuckDB
- `load_positions`: query `positions_history` and return only the **latest snapshot per instrument**. Use a SQL window function, DuckDB `QUALIFY`, or a correlated subquery (no Python-side filtering).
- `load_prices`: read the raw parquet file
- `clean_prices`: fix the data quality issues in the raw price file (missing values, duplicates, outliers). Document your strategy.
- `load_scenarios`: read the scenarios parquet

### 2. Risk metrics

Implement the six functions in `src/risk_metrics.py`:

- `compute_var_historical` / `compute_cvar_historical`
- `compute_var_parametric` / `compute_cvar_parametric`
- `compute_component_var`: Euler decomposition of portfolio VaR by position
- `kupiec_pof_test`: Kupiec Proportion of Failures test for backtesting

### 3. Backtesting

Implement `run_rolling_backtest` in `src/backtest.py`:

- Rolling 60-day estimation window
- Historical VaR at 99% confidence
- Count breaches and apply the Kupiec test
- Collect breach dates for visualization

### 4. Stress testing

Implement `apply_scenarios` in `src/stress.py`. Join the 3 predefined scenarios from `scenarios.parquet` with the current positions, compute the portfolio return and CHF P&L per scenario, and return a per-scenario summary. Expect to discuss in the interview which scenario is most damaging to this portfolio and why.

### 5. Reporting

Implement the writers in `src/reporting.py`. Produce the required output files (JSON, CSV, PNG, TXT).

### 6. Containerization

Fill in `Dockerfile` and `docker-compose.yml` so that `docker compose up --build` populates `./output/` on the host. Expect questions on your Dockerfile choices (base image, layer ordering, user, environment variables).

### 7. Report writing

Complete `REPORT.md` (template provided). If you skipped any section or ran out of time, add a short "What I would do with more time" paragraph. This helps us calibrate.

## Notes on conventions

- **Log vs simple returns**: Either is acceptable. Be consistent.
- **VaR sign convention**: Report VaR and CVaR as **positive numbers** representing losses (industry standard).
- **Component VaR grouping**: Decompose by `sub_class` from the instruments table (5 buckets: `SWISS_EQUITY`, `EUR_EQUITY`, `CHF_GOVT`, `EUR_GOVT`, `CHF_CORP`).
- **Plots**: use matplotlib for PNG output. Set the `Agg` backend so plots render in a headless container (`matplotlib.use("Agg")` before importing pyplot).

## Submission

When your work is ready for review:

```bash
# Make sure your branch builds cleanly one last time
docker compose down
docker compose up --build

# Commit any remaining work (example)
git status
git add -A
git commit -m "Final adjustments before submission"

# Push your branch
git push -u origin candidate/<your-firstname-lastname>
```

Then reply to the recruiter email to confirm your branch is ready. Do **not** open a pull request against `main`. We review the branch directly.

### What we look for in your commit history

Commit as you work, one commit per logical unit. The git history is part of the evaluation:

- **Meaningful commit messages**: `Implement historical VaR and CVaR` beats `wip` or `fix`
- **Atomic commits**: one commit does one thing (implement a function, add tests, fill in the Dockerfile)
- **Incremental progress**: a single end-of-work `Add everything` commit is a weak signal
- **Clean history**: you can rebase or squash trivial commits (`fix typo`, `wip`) before pushing, but do not erase meaningful progress

### What *not* to commit

The `.gitignore` excludes the common culprits, but double-check:

- No `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ipynb_checkpoints/`
- No credentials or `.env` files
- No large binary outputs in `output/` (only the placeholder `.gitkeep`)
- No OS junk (`.DS_Store`, `Thumbs.db`)

If you accidentally committed something you should not have, amend or revert before pushing. We read the git log.

## Questions?

If you have any questions about the assessment, contact the hiring manager.
