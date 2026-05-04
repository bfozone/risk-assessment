# Risk Analysis Report: Multi-Asset Fund

**Analyst:** _(your name)_
**Date:** _(date)_
**Time spent:** _(approximate hours, used for calibration, not evaluation)_
**What I prioritized:** _(one or two sentences on what you focused on and what you left as stretch or skipped)_

---

## 1. Executive Summary

_5–10 sentences for the CRO. Cover: key risk metrics, VaR model performance, main vulnerabilities revealed by stress testing, and recommended actions._

## 2. Risk Metrics and Method Comparison

_Brief commentary on the differences between historical and parametric VaR/CVaR. Which do you trust more for this portfolio and why? What are the implications of the observed skewness/kurtosis?_

## 3. Backtest Findings

_What does the 60-day rolling VaR backtest tell you? Was the Kupiec test rejected? What improvements would you suggest for a production risk system?_

## 4. Production Architecture

_Sketch how you would run this analysis daily at 7:00 AM in production. Consider:_
_- Data ingestion (sources, scheduling, quality checks)_
_- Orchestration_
_- Storage (raw data, computed metrics, historical time series)_
_- Compute engine_
_- Output: dashboards, reports, alerts_
_- Monitoring and reliability_
_- Deployment and CI/CD_

_Reference specific tools or technologies you would use. Any coherent modern stack is fine._
