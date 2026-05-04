# Risk Analysis Report: Multi-Asset Fund

**Analyst:** _LukaszWawryszuk_
**Date:** _04052026_
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

