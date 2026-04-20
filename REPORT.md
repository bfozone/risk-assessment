# Risk Analysis Report: Multi-Asset Fund

**Analyst:** Martin Diergardt
**Date:** 2026-04-20
**Time spent:** ~30 hours
**What I prioritized:** Core pipeline correctness and depth of analysis — complete statistical backtest (Kupiec, Christoffersen CC, ES coverage, Basel traffic light), instrument-level P&L attribution on breach days, and scenario coverage gap analysis.

**Stretch items completed:** stretch output files (backtest.json, backtest.png, correlation heatmap, summary.txt), own tests beyond the provided suite (`test_risk_metrics_stretched.py`, `test_data_loader_stretched.py`), extended methodology (EWMA-filtered historical simulation, Christoffersen conditional coverage, ES backtest), Docker with separate test service.

**Stretch items skipped:**

- *Benchmark-relative risk* (tracking error, active risk decomposition vs benchmark): `portfolio_meta` defines the benchmark as "Custom Composite (40% SPI / 60% SBI)" but neither SPI nor SBI return series are present in the data files — `prices.parquet` contains only the 18 portfolio instruments. The analysis is blocked by missing benchmark data. With SPI and SBI prices sourced (Bloomberg/Refinitiv), active weights and tracking error could be computed directly from the existing covariance infrastructure.
- *Container polish* (non-root user, multi-stage build): non-root user requires UID matching on the bind-mounted output volume; multi-stage build would separate the uv dependency layer from the runtime image.

---

## 1. Executive Summary

The portfolio carries **CHF 8.5M in daily tail risk** (historical CVaR 99%, CHF 500M NAV). Risk is heavily concentrated: SWISS\_EQUITY accounts for 66% of component VaR, with government bonds providing a modest diversification offset. The VaR model **fails Kupiec** (7 breaches vs 1.9 expected; p = 0.0045) and is in the **Basel Yellow zone** (×3.62 capital multiplier), driven by a Sep–Nov 2025 volatility regime shift that the 60-day estimation window was too slow to absorb. ES systematically underestimates tail severity by 25% (coverage ratio 1.25×, 95% CI [1.10, 1.47]). Stress testing reveals two structural vulnerabilities: the fixed-income allocation amplifies — not hedges — a rates-driven shock (SNB scenario: −CHF 24.5M), and sovereign and IG corporate bond hedges diverge in a European fiscal crisis. Immediate actions required: MRM escalation per Kupiec FAIL protocol, a stressed ES overlay to address the 25% tail under-coverage, and single-name concentration reviews for NOVN, ROG, and UBSG.

---

## 2. Risk Metrics and Method Comparison

| Metric | Historical | Parametric | Gap |
| -------- | ----------- | ------------ | ----- |
| VaR 95% | 0.95% | 1.05% | −0.10% |
| CVaR 95% | 1.47% | 1.31% | +0.16% |
| VaR 99% | **2.02%** | 1.47% | **+0.54%** |
| CVaR 99% | **2.39%** | 1.69% | **+0.70%** |

*Full derivations: `documentation/risk_metrics_methodology.md`. Interactive notebook: `notebooks/risk_metrics_explained.ipynb`.*

The 37% gap between historical and parametric VaR at 99% is driven by the portfolio's excess kurtosis of 5.9 (normal = 0) and mild negative skewness. The parametric model — which assumes Gaussian returns — materially understates tail risk at high confidence levels. Historical simulation is the more reliable estimate for this portfolio.

**Component VaR (99%, Euler decomposition)** confirms the concentration:

| Sub-class | Component VaR | % of Total |
| ----------- | -------------- | ------------ |
| SWISS\_EQUITY | 0.96% | 66% |
| EUR\_EQUITY | 0.47% | 33% |
| CHF\_CORP | 0.05% | 3% |
| CHF\_GOVT | −0.01% | — |
| EUR\_GOVT | −0.01% | — |

Government bonds carry negative component VaR — they diversify — but their allocation is too small to materially reduce total risk. The portfolio is an equity-beta vehicle with a partial bond hedge.

---

## 3. Backtest Findings

*Full results and breach-level attribution: `documentation/VaR_backtest_result.md`. Notebook: `notebooks/backtest_explained.ipynb`.*

**Model verdict: FAIL.** Flat historical simulation (99%, 60-day window) produced 7 breaches over 192 days against 1.9 expected.

| Test | Statistic | p-value | Result |
| ------ | ----------- | --------- | -------- |
| Kupiec POF — flat HS | LR = 8.09 | 0.0045 | **FAIL** |
| Kupiec POF — EWMA HS (λ = 0.94) | LR = 5.60 | 0.0179 | **FAIL** |
| Christoffersen independence (lag-1) | LR = 0.53 | 0.47 | PASS |
| Conditional Coverage | LR = 8.62 | 0.013 | **FAIL** |
| ES coverage ratio | 1.25× | CI [1.10, 1.47] | **FAIL** |
| Basel Traffic Light | 7 breaches / 192d | — | **YELLOW ×3.62** |

The breaches fall into two distinct episodes:

- **Jul 2025 (×2):** calm, low-vol regime — the 60-day window produced a VaR that was too tight even for moderate moves. EWMA rescaling has no meaningful effect in a calm regime.
- **Sep–Nov 2025 (×4):** wholesale volatility regime shift from ≈5% to ≈16% annualized. The estimation window could not respond fast enough. EWMA reduces this cluster by one breach but cannot resolve the regime-lag within a 60-day window.

P&L attribution on breach days identifies three structural findings: (1) UBSG is a top-two detractor on 5 of 7 breach dates — concentration warrants a single-name limit review; (2) the sovereign bond hedge fails in a rates-driven shock (Jul 7: bonds compounded the loss) and is dormant in an equity-idiosyncratic event (Oct 1: no flight-to-quality bid); (3) on Oct 16, IG corporate bonds widened while sovereigns rallied — the two should not be treated as a single fixed-income hedge.

**Recommended improvements:**

1. Escalate to MRM per Kupiec FAIL protocol.
2. Add stressed ES overlay (GFC 2008–09 or Mar 2020 stress period) to address 25% tail under-coverage.
3. Evaluate GARCH(1,1) or a two-component EWMA (λ = 0.94 calm / 0.97 stressed) as the production vol model.
4. Implement a 10-day rolling breach-rate monitor to detect multi-week clustering that lag-1 independence tests cannot capture.

---

## 4. Stress Testing

*Full scenario results and attribution: `documentation/Stress_results.md`. Methodology: `documentation/Stress_methodology.md`. Notebook: `notebooks/stress_explained.ipynb`.*

| Scenario | Portfolio Return | P&L (CHF M) |
| ---------- | ----------------- | ------------- |
| Global Equity Market Crash | −5.09% | −25.4 |
| SNB Emergency Rate Hike (+100bp) | −4.91% | −24.5 |
| European Sovereign Debt Stress | −2.49% | −12.4 |

Scenarios exceed 1-day VaR by 1.2× to 2.5×, indicating events beyond routine daily tail risk. Against the 10-day Basel horizon (√10-scaled VaR of 6.37% / CHF 31.9M), however, all three scenarios fall below VaR — the library is calibrated at the mild end of the stress spectrum and would benefit from more severe historical-crisis scenarios (2008, 2020).

Three structural findings:

1. **The SNB rate hike is nearly as severe as the equity crash.** In a rates-driven shock, the fixed-income allocation (≈37% of NAV) becomes a source of loss, not a hedge. Duration risk materializes across the entire bond book simultaneously. This directly mirrors the Jul 7, 2025 backtest breach — the portfolio is implicitly long duration and that duration is unhedged.

2. **The sovereign hedge works in an equity crash but is undersized.** CHF government bonds provide +101 bps offset against ≈−634 bps in equity losses. The diversification benefit is real but insufficient to materially reduce the tail outcome.

3. **EU sovereign stress exposes a structural split within fixed income.** CHF government bonds rally while European government bonds sell off. IG corporate bonds also widen. Sovereign and credit hedges must be modeled and sized separately.

**Scenario library gaps:** the current three-scenario library covers "equities down" in three flavors but leaves four risk factors unaddressed: standalone credit spread widening, CHF appreciation (direct FX impact on EUR-denominated positions), a liquidity crunch (correlated sell-off with no flight-to-quality offset), and an inflation shock (rates up and equities down simultaneously). A minimum of 5–8 scenarios is required for a FINMA/Basel III-compliant library. See `documentation/Stress_methodology.md` §3.2 for detailed specifications.

---

## 5. Production Architecture

*Current containerized pipeline: `documentation/docker.md`. Run with `docker compose up --build`.*

**Target: outputs available before market open at 08:00.**

```Text
Data ingestion (07:45)
  Bloomberg / Refinitiv feed → raw prices appended to on-premise parquet store
    (Apache Iceberg on NAS/HDFS — time-travel supports audit trails and
    regulatory data retention of 5–7 years as required under FINMA and Basel III)
  Data quality checks: staleness, missing instruments, price spike detection
  Failure → email alert to risk team; previous-day snapshot used as fallback

Orchestration
  Cron job or lightweight scheduler triggers at 07:50
  Step dependencies: data quality → risk compute → report generation
  Retry policy: 2× with 2-minute backoff; email alert on second failure

Compute
  Containerised Python (this repo's Dockerfile, pinned via uv.lock)
  CPU-only; < 30 seconds for the current 18-instrument, 252-day dataset
  The container accepts --output-dir and exits — it has no knowledge of
  schedules, retries, or dependencies. The scheduler calls it like any
  command-line process. This separation means the same image runs locally
  (docker compose up), in CI (docker run), and in production without
  modification; if the scheduler changes, the compute logic is unaffected.

Storage
  Raw prices: append-only Iceberg table on on-premise object store or NAS
  Computed metrics (risk_metrics.json, backtest.json, scenarios.csv):
    written to a Postgres time-series table for trending and audit
  Retention: 5–7 years for computed risk metrics (FINMA / Basel III);
    raw price data retained for the full regulatory period

Output
  Daily PDF report: generated from summary.txt + charts via nbconvert, emailed via SMTP to CRO and risk team by 08:00
  Existing BI tool (Power BI / Tableau / Excel): consumes scenarios.csv
    and risk_metrics.json directly — no additional dashboard infrastructure
    required if the organization already has a standard tooling
  Alerts: VaR breach or pipeline failure → email via SMTP;
    Teams webhook if the organization is on Microsoft 365

Monitoring and reliability
  Pipeline health: success/failure email on every run
  Data quality: staleness and completeness checks on ingestion (price spike
    detection flags potential data errors before they reach the risk numbers)
  Run history logged to Postgres for audit purposes

CI/CD
  GitHub Actions: lint (ruff) + type check (basedpyright) + tests on every PR
  Docker image pushed to a private registry (GitHub Container Registry) on merge to main
  The existing test suite (docker compose run tests) is the primary
  regression guard — sufficient for the current pipeline scope
```
