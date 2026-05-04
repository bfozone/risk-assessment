# Risk Analysis Report: Multi-Asset Fund

**Analyst:** _LukaszWawryszuk_
**Date:** _04/05/2026_
**Time spent:** _2days_
**What I prioritized:** _Data quality, data understanding, results validation, python/Docker configuration_

---

## 1. Executive Summary

_This report evaluates the risk profile for the CHF 500M Multi-Asset Fund. Our primary 99% Historical Value at Risk (VaR) indicates a maximum expected daily loss of CHF 10.4mn under normal market conditions. However, backtesting of the 60-day rolling VaR model over the last 192 days reveals significant under-calibration, with 7 observed breaches against an expected 1.92 (Kupiec proportion of failures test statistically rejects the model's validity). Model would work much better for a longer rolling period. Stress testing highlights severe portfolio vulnerabilities to a Global Equity Market Crash (projected loss: CHF 25.5M) and a 100bps SNB Emergency Rate Hike (projected loss: CHF 24.6M)._

## 2. Risk Metrics and Method Comparison

_The 99% Historical VaR (2.09%) is substantially higher than the 99% Parametric VaR (1.48%). Because parametric VaR assumes a perfectly normal distribution, its lower value indicates that our portfolio suffers from "fat tails" (excess kurtosis) or negative skewness. The models capturing actual historical events predict far larger risks. Historical expected shortfall predicts an average tail loss of 2.49% (CHF 12.47M). Model Recommendation: I trust the Historical and EWMA models significantly more for this portfolio. The EWMA CVaR model (99% VaR of 2.46%) effectively up-weights recent volatility, making it responsive to current market conditions without relying on the dangerous assumption of normality._

## 3. Backtest Findings

_Over 192 observations, the model experienced 7 breaches (an observed failure rate of 3.65% instead of the targeted 1%). The Kupiec test statistic is 8.087 with a p-value of 0.0045, leading to a definitive rejection of the null hypothesis. A 60-day window is too short. A single shock heavily skews the threshold, and as soon as that shock falls out of the 60-day window, the VaR artificially drops, leaving the fund exposed. We should transition to a standard 250-day (1-year) historical window.Volatility Scaling would be beneficial. Implement Filtered Historical Simulation (FHS) to scale historical returns by current market volatility, reducing the clustering of breaches during volatile regimes._

## 4. Production Architecture

_To meet a 7:00 AM deadline, ingestion should ideally be an ongoing process at 3 am to allow for buffer time. Heavy calculations should be triggered overnight, e.g. at 4am. Sources: market data APIs, internal DBs, and flat files like CSVs/JSON/XML 3rd party providers. Quality checks:number of files,file size,number of rows,portfolio mv change, aggregated position mv change, price outliers, stale prices, missing prices_

_Orchestration: raw data loader -> data cleaning -> data quality dashboard ->risk metrics and backtesting / stress testing-> reporting and visualisations_
_- Storage: market data might be stored in the cloud (AWS, Google), highly sensitive data like trades, positions should be stored on a local server: PostgreSQL, Microsoft SQL, Oracle_
_- Compute engine: Snowflake for SQL-heavy risk metrics, Databricks (Spark) allows to run Python for heavy-duty Monte Carlo simulations or Value at Risk (VaR) calculations._
_- Output: Dashboards in BI platform like Tableau/QlickSense  or python solution e.g. Stramlit, Dash. Reports in PDF format. Alerts like breached limits communicated officially vis email and stored locally._
_- Monitoring and reliability: FastAPI dashboard with stats and visualizations for data quality and risk metrics_
_- Deployment and CI/CD: GitHub which automatically runs tests on your Python/SQL code._







# Risk Analysis Report: Multi-Asset Fund

| | |
|---|---|
| **Analyst** | _Lukasz Wawryszuk_ |
| **Date** | _04/05/2026_ |
| **Time spent** | _2 longer days_ |
| **AI usage** | Claude used to scaffold functions, recall formulas, and draft sections. Every function and claim reviewed and understood before submission. |
| **What I prioritised** | Data quality, data understanding, results validation, python/Docker configuration. Core pipeline correctness. EWMA-weighted VaR added as the primary stretch item. Correlation heatmap, backtest plot, and summary.txt included as additional stretch outputs. |

---

## 1. Executive Summary

The flagship multi-asset fund (CHF 500M, Swiss and European equities and bonds) was analysed over less then one year of daily price history across 18 instruments. At 99% confidence, the fund's one-day Value-at-Risk is **2.09% (CHF 10.4M)** on a historical basis and **1.48% (CHF 7.4M)** parametrically. The large gap between the two — 41 basis points — is a significant and meaningful divergence explained below.

The 60-day rolling backtest recorded **7 breaches over 192 observation days** against an expectation of 1.9. The Kupiec LR statistic is **8.09** (p-value **0.0045**), firmly rejecting H₀ at the 1% level. The model is undercalibrated — it systematically underestimates tail losses. The primary cause is the short 60-day estimation window initialised during a calm period.

Stress testing reveals the **Global Equity Market Crash** scenario as the most damaging event, producing a simulated loss of **CHF 25.5M (−5.09%)**, closely followed by the **SNB Emergency Rate Hike** at **CHF 24.5M (−4.91%)**. Component VaR confirms that Swiss equities alone account for **65% of total parametric VaR**, making equity concentration the fund's dominant structural risk.

**Recommended actions:** extend the estimation window to at least 250 days, adopt historical VaR (not parametric) as the primary metric given the fat-tailed return distribution, incorporate EWMA VaR (λ = 0.97) as a real-time complement, and review the Swiss equity overweight relative to the benchmark.

---

## 2. Risk Metrics and Method Comparison

### Results summary

| Method | Confidence | VaR | CVaR | VaR (CHF) | CVaR (CHF) |
|--------|-----------|-----|------|-----------|------------|
| Historical | 95% | 0.96% | 1.52% | 4.8mn | 7.6mn |
| Historical | 99% | **2.09%** | **2.49%** | **10.4mn** | **12.5mn** |
| Parametric | 95% | 1.06% | 1.32% | 5.3mn | 6.6mn |
| Parametric | 99% | 1.48% | 1.70% | 7.4mn | 8.5mn |
| EWMA λ=0.97 | 95% | 0.95% | 1.28% | 4.8mn | 6.4mn |
| EWMA λ=0.97 | 99% | 1.26% | 2.06% | 6.3mn | 10.3mn |

---

### Historical vs Parametric

**Historical simulation** makes no assumption about the shape of the return distribution — it takes the empirical 1st percentile of past returns directly. Its main weakness is equal-weighting: every past day counts the same regardless of how long ago it occurred.

**Parametric (variance-covariance)** assumes returns follow a normal distribution. It is simple and produces smooth estimates, but the normality assumption is known to understate tail risk.

**Key observation from the actual data:** historical 99% VaR (2.09%) is **41 basis points higher** than parametric (1.48%) — a 41% difference in CHF terms (CHF 10.4M vs CHF 7.4M). This is the opposite of what a normal distribution would predict, and it is telling. It means the actual return distribution has **fat tails**: extreme losses occur more often and are larger than a normal distribution would imply. The parametric model is materially underestimating risk and should not be used as the primary VaR metric for this portfolio.

This is also why the backtest rejects the model — the VaR estimate being used in the backtest is the historical one (2.09%), yet it still produces 7 breaches. If the parametric estimate (1.48%) were used instead, breach count would be even higher.

Historical simulation is clearly preferred here. However, one year of data is insufficient — the Basel III minimum is 250 business days, with many institutions using 500 or more. The EWMA variant (λ = 0.97) should be added as a real-time signal.

---

### EWMA-Weighted VaR

EWMA VaR addresses the main weakness of plain historical VaR by exponentially down-weighting older returns. A decay factor λ = 0.98 gives a return from 100 days ago roughly 13% of the weight of today's return.

| Decay | Behaviour | Best used when |
|-------|-----------|---------------|
| λ = 0.99 | Slow fade, long memory | Stable volatility regimes, conservative risk management |
| λ = 0.97 | Fast fade, reacts quickly | After a market spike; avoids holding inflated VaR too long |

---

### Component VaR by Sub-Class

Component VaR (Euler decomposition) decomposes total portfolio VaR into additive contributions by asset class. Key property: the five sub-class contributions sum exactly to total parametric VaR.

| Sub-class | Component VaR | Share of total | Direction |
|-----------|--------------|---------------|-----------|
| SWISS_EQUITY | +0.0096 | **65%** | Risk-adding |
| EUR_EQUITY | +0.0047 | **32%** | Risk-adding |
| CHF_CORP | +0.0005 | 3% | Risk-adding |
| CHF_GOVT | −0.0002 | — | **Diversifying** |
| EUR_GOVT | −0.0001 | — | **Diversifying** |
| **Total** | **+0.0145** | 100% | |

The results are unambiguous: **Swiss equities are the dominant risk driver** at 65% of total VaR, with European equities adding another 32%. Together they account for 97% of portfolio risk. Both government bond buckets show **negative** component VaR — they are actively reducing portfolio risk through their negative correlation with equities. This is the classic flight-to-safety dynamic: when equities fall, government bonds tend to rise. CHF corporate bonds add a small positive contribution, behaving more like equities than safe-haven bonds.

---

## 3. Backtest Findings

### Results

| Metric | Value |
|--------|-------|
| Estimation window | 60 days |
| Confidence level | 99% |
| Backtest period | 192 days |
| Expected breaches | 1.92 |
| Observed breaches | **7** |
| Observed breach rate | 3.65% (vs 1.00% expected) |
| Kupiec LR statistic | **8.09** |
| Kupiec p-value | **0.0045** |
| H₀ rejected at 5%? | **Yes — model is undercalibrated** |

**Breach dates:** 7 Jul 2025, 15 Jul 2025, 22 Sep 2025, 1 Oct 2025, 16 Oct 2025, 11 Nov 2025, 20 Feb 2026

Note the clustering: 2 breaches in July, 3 in Sep–Oct, 1 in November — three distinct stress episodes rather than 7 randomly scattered events. This clustering pattern is itself informative: it suggests **volatility regime changes**, not random model noise.

---

### Interpretation

A 99% VaR model should produce breaches on roughly 1% of days. With 7 breaches against an expectation of 1.9, the observed rate is approximately 3.6× the expected rate. The Kupiec Proportion of Failures test formally rejects the null hypothesis that the model is correctly calibrated.

**Four likely causes, in order of probability:**

1. **Short estimation window (primary cause).** A 60-day window initialised during a calm period systematically underestimates VaR. The model has not "seen" any stress events when it starts, so early VaR estimates are too low. When volatility arrives, breaches cluster before the window catches up.

2. **Volatility clustering.** Financial market volatility is not evenly distributed — bad days tend to follow bad days. Equal-weight historical VaR reacts slowly to regime changes. This is precisely the argument for EWMA VaR.

3. **Fat tails / insufficient tail data.** With 60 observations, the 1% tail contains fewer than 1 observation on average. The VaR estimate is extremely noisy.

4. **Static weights applied to history.** The pipeline uses the latest portfolio weights throughout the entire historical return calculation. The fund rebalanced quarterly, so historical portfolio returns do not match what was actually earned — this introduces a bias of unknown direction.

---

### Suggested production improvements

| Improvement | Rationale |
|-------------|-----------|
| Extend window to 250 days | Basel III minimum; captures a full market cycle |
| Add EWMA VaR alongside historical | Faster reaction to volatility spikes |
| Use time-varying weights | Reconstruct historical portfolio returns using the weights that were actually in effect on each date |
| Expected Shortfall backtest | Regulators (FRTB) now require ES (CVaR) backtesting, not just VaR |

---

## 4. Stress Testing Results

| Scenario | Portfolio Return | P&L (CHF) | Severity |
|----------|-----------------|-----------|---------|
| Global Equity Market Crash | **−5.09%** | **−25,450,000** | 🔴 Most severe |
| SNB Emergency Rate Hike (+100bp) | −4.91% | −24,545,000 | 🔴 Very severe |
| European Sovereign Debt Stress | −2.49% | −12,450,000 | 🟡 Moderate |

### Key findings

**The equity crash and rate hike scenarios are nearly equal in severity** (CHF 25.5M vs CHF 24.5M), which is counterintuitive. Rate hike scenarios typically hurt bond-heavy portfolios more than equity-heavy ones. Here, however, the SNB rate shock also hits Swiss equities hard (Swiss corporates are sensitive to domestic financing costs), explaining why the damage approaches the equity crash level.

**The sovereign debt scenario (CHF 12.5M) is half the severity** of the other two. This is consistent with the portfolio's relatively low allocation to EUR government bonds and its Swiss equity dominance — European sovereign stress is less directly damaging to Swiss large-caps than a global equity drawdown.

**All three scenarios result in losses well above the 99% historical VaR of CHF 10.4M**, confirming that stress scenarios capture tail events that VaR does not. The equity crash loss (CHF 25.5M) is 2.4× the daily VaR — plausible for a multi-day correlated drawdown compressed into a single-day shock.

---

## 5. Production Architecture

---

### Daily Schedule

| Time | What happens |
|------|-------------|
| 3:00 AM | Data collection begins — market prices, positions, and reference data are pulled from all sources |
| 4:00 AM | Heavy calculations start — risk metrics, backtesting, and stress scenarios run overnight when compute is cheap and uncontested |
| 6:30 AM | Reports and dashboards are finalised and alerts are sent if any limits have been breached |
| 7:00 AM | Results are ready for the morning meeting |

---

### Data Sources

Data arrives from three types of source:

- **Market data APIs** — real-time or end-of-day price feeds (e.g. Bloomberg, Refinitiv)
- **Internal databases** — trades, positions, and portfolio metadata maintained by the firm's own systems
- **Flat files** — CSVs, JSON, or XML files delivered by third-party data providers (index providers, rating agencies, etc.)

---

### Data Quality Checks

Before any calculation runs, every incoming data file is validated. If a check fails, the pipeline stops and an alert is sent — it is safer to delay the report than to publish numbers based on bad data.

| Check | What it catches |
|-------|----------------|
| File count and size | Missing or truncated files from a provider |
| Row count | Unexpectedly few or many records |
| Portfolio market value change | Large overnight NAV swings that may indicate bad prices |
| Position market value change | Individual position moves that look implausible |
| Price outliers | Fat-finger errors or stale feed values |
| Stale prices | Instruments whose price has not updated in more than one day |
| Missing prices | Instruments with no price at all for today |

---

### Pipeline Steps (Orchestration)

Each step runs in sequence. If any step fails, the rest are cancelled and the team is notified automatically.

```
Raw data collected from all sources
        ↓
Data cleaning  (remove duplicates, fill gaps, fix outliers)
        ↓
Data quality dashboard updated  (team can see what passed/failed)
        ↓
Risk metrics calculated  ──┐
Backtesting runs           ├─ these run in parallel to save time
Stress scenarios applied  ──┘
        ↓
Reports generated and dashboards refreshed
        ↓
Breach alerts sent by email if any limits are exceeded
```

---

### Storage

Where data is kept depends on how sensitive it is:

| Data type | Where | Why |
|-----------|---------------|-----|
| Market prices, reference data | Cloud storage (AWS S3 or Google Cloud) | Scalable, easy to share across systems |
| Trades, positions, portfolio holdings | On-premise server (PostgreSQL, Microsoft SQL Server, or Oracle) | Highly sensitive — kept behind the firm's own firewall |
| Computed risk metrics | On-premise database | Queryable history of daily VaR and other metrics |
| Published reports | Cloud (with access controls) | Easy to distribute to stakeholders |

---

### Compute Engine

Two tools handle the calculations depending on complexity:

- **Snowflake** — handles SQL-based risk calculations efficiently at scale; good for aggregations, joins, and structured queries across large datasets
- **Databricks (Apache Spark)** — used for heavy Python workloads such as Monte Carlo simulations or large historical VaR calculations across thousands of instruments; can distribute the work across many machines in parallel

---

### Outputs

| Audience | What they receive |
|----------|------------------|
| Portfolio managers / CRO | Interactive dashboard (Tableau, Qlik Sense) or a Python-built web app (Streamlit, Dash) updated each morning |
| All stakeholders | Automated PDF report delivered by email before 7:00 AM |
| Risk and compliance teams | Email alerts for any breached limits, archived locally for the audit trail |

---

### Monitoring and Data Quality Dashboard

A lightweight internal web dashboard (built with FastAPI) gives the risk team a live view of the pipeline's health each morning — which data quality checks passed or failed, whether calculations completed on time, and a summary of that day's key metrics and visualisations. This means any issue is visible immediately without needing to dig through log files.

---

### Code and Deployment (CI/CD)

All code lives in **GitHub**. Whenever a developer proposes a change, GitHub automatically runs the full test suite against the updated code before it is allowed to go live. This ensures that a bug introduced in one place does not silently break the morning run — the pipeline only updates when all tests pass.
