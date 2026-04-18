# VaR Backtest Results

**Portfolio:** Multi-asset Swiss equity and fixed-income portfolio  
**Backtest period:** 2025-06-24 → 2026-03-18 (192 trading days)  
**VaR model:** Historical simulation, 99% confidence, 60-day estimation window  
**Methodology reference:** `VaR_backtesting_methodology.md`

---

## Executive Summary

**Model verdict.**  Flat historical simulation VaR (99%, 60-day window) produced **7 breaches** over 192 trading days against 1.9 expected — Kupiec LR = 8.09, p = 0.0045, Basel Yellow zone (×3.62 capital multiplier).  EWMA-filtered HS reduces this to 6 breaches (p = 0.0179, ×3.51 multiplier) but remains in Yellow.  Both models fail Kupiec at the 5% level.  The Conditional Coverage test also fails (LR = 8.62, p = 0.013), driven entirely by the Kupiec frequency component — the Christoffersen independence test passes (p = 0.47), confirming no next-day breach clustering.  ES systematically underestimates tail severity by 25% (coverage ratio 1.25×, 95% CI [1.10, 1.47]), a bias driven by the Sep–Nov 2025 volatility regime shift.

**Portfolio findings.**  The seven breaches fall into two distinct risk episodes: two low-vol regime exceptions in July 2025 (estimation window vol ≈ 5.4% annualised — VaR was too tight even for moderate moves) and a four-breach Sep–Nov 2025 cluster triggered by a wholesale volatility regime shift to ≈16%.  UBSG ranks among the top-two detractors on five of seven breach days; NOVN and ROG dominate the Oct–Nov cluster.  On Oct 16, IG corporate and sovereign bond offsets diverged — sovereigns rallied while corporate spreads widened simultaneously — indicating the fixed-income hedge cannot be treated as a single aggregate across instruments.

**Recommended actions.**  (1) Escalate to Model Risk Management per Kupiec FAIL protocol.  (2) Apply a stressed ES overlay (GFC 2008–09 or Mar 2020) to correct the 25% tail under-coverage.  (3) Evaluate EWMA with a two-component λ mix (0.94 calm / 0.97 stressed) or GARCH(1,1) as the production volatility model.  (4) Extend the backtest horizon to 250 days for direct Basel comparison without threshold scaling.  (5) Commission single-issuer concentration reviews for NOVN, ROG, and UBSG.

---

## 1. Backtest Summary Statistics

| Metric | Value |
|--------|-------|
| Backtest period | 2025-06-24 → 2026-03-18 |
| Estimation window | 60 days |
| Confidence level | 99% |
| Observations | 192 |
| Expected breaches | 1.9 |
| Observed breaches | 7 |
| Observed breach rate | 3.65% |

### Breach Dates

| Date | Realised return | VaR estimate | Excess loss |
|------|----------------|-------------|-------------|
| 2025-07-07 | −0.70% | — | — |
| 2025-07-15 | −0.65% | — | — |
| 2025-09-22 | −1.24% | — | — |
| 2025-10-01 | −2.00% | — | — |
| 2025-10-16 | −2.50% | 1.55% | 0.95% |
| 2025-11-11 | −2.65% | — | — |
| 2026-02-20 | −1.13% | — | — |

---

## 2. Statistical Test Results

### 2.1 Kupiec POF Test

| Metric | Flat HS | EWMA HS (λ=0.94) |
|--------|---------|------------------|
| Observations | 192 | 192 |
| Expected breaches | 1.9 | 1.9 |
| Observed breaches | **7** | **6** |
| Observed rate | 3.65% | 3.13% |
| LR statistic | 8.09 | 5.60 |
| p-value | 0.0045 | 0.0179 |
| Critical value χ²(1), 5% | 3.84 | 3.84 |
| **Verdict** | **FAIL** | **FAIL** |

EWMA vol-scaling removes one breach and reduces the LR statistic by 2.5 points but cannot move either model out of the Yellow zone. The Jul 2025 exceptions occur in a calm, low-vol regime where rescaling has minimal effect; the Sep–Nov cluster is only partially absorbed within a 60-day window.

### 2.2 Christoffersen Independence Test (Lag-1)

| Metric | Value |
|--------|-------|
| n00 (no breach → no breach) | 184 |
| n01 (no breach → breach) | 7 |
| n10 (breach → no breach) | 7 |
| n11 (breach → breach) | **0** |
| P(breach \| no breach yesterday) | 3.66% |
| P(breach \| breach yesterday) | 0.00% |
| LR statistic | 0.53 |
| p-value | 0.4655 |
| **Verdict** | **PASS** |

n11 = 0 — no two consecutive days were both breaches. The Sep–Nov cluster (Sep 22, Oct 1, Oct 16, Nov 11) was separated by 9, 15, and 26 trading days respectively, placing it entirely outside the lag-1 detection window.

### 2.3 Conditional Coverage Test

| Metric | Value |
|--------|-------|
| LR_cc = LR_pof + LR_ind | 8.09 + 0.53 = **8.62** |
| p-value | 0.0134 |
| Critical value χ²(2), 5% | 5.99 |
| **Verdict** | **FAIL** |

The CC failure is entirely Kupiec-driven, not independence-driven. The independence test contributes only 0.53 / 8.62 = 6% of the joint LR statistic.

### 2.4 Christoffersen-Pelletier Duration Test

| Metric | Value |
|--------|-------|
| Inter-breach durations (trading days) | [8, 53, 9, 15, 26, 71] |
| Observed mean duration | 30.3 days |
| Expected mean duration (H₀, 99% VaR) | 100 days |
| Fitted Weibull shape â | < 1.0 |
| LR_uc (coverage, χ²(1)) | — |
| LR_ind (duration independence, χ²(1)) | — |
| LR_cc (joint, χ²(2)) | — |

> **Power caveat:** only 6 inter-breach durations are available. The Weibull MLE is noisy at n = 6, and the test has limited power to reject H₀ even when clustering is present. Results should be read directionally, not as conclusive inference. A minimum of ~10 durations (≈ 4 years at 99% VaR) is needed for reliable inference.

### 2.5 ES Coverage Test

| Metric | Value |
|--------|-------|
| Breach days used | 7 |
| Mean realised loss | — |
| Mean ES estimate | — |
| **Coverage ratio** | **1.251×** |
| Bootstrap 95% CI | [1.098×, 1.471×] |
| Reject H₀ (CI entirely > 1.0) | **Yes** |
| **Verdict** | **FAIL** |

The coverage ratio of 1.25× indicates the model underestimates average tail severity by 25% on breach days. The CI lies entirely above 1.0, providing strong evidence that this under-coverage is systematic rather than a sampling artefact. The bias is concentrated in the Sep–Nov cluster, where ES estimates were calibrated on the preceding calm-vol window.

### 2.6 Basel Traffic Light

| Metric | Flat HS | EWMA HS |
|--------|---------|---------|
| Observations | 192 | 192 |
| Observed breaches | 7 | 6 |
| Green threshold (≤) | 2 | 2 |
| Yellow threshold (≤) | 5 | 5 |
| **Zone** | **YELLOW** | **YELLOW** |
| Capital multiplier add-on | +0.62 | +0.51 |
| Effective multiplier (3.0 + add-on) | **×3.62** | **×3.51** |

> Note: thresholds are scaled from the Basel 250-day standard using equivalent binomial CDF levels (Green ≈ 89.1%, Yellow ≈ 99.99%) applied to Binomial(192, 0.01). The 250-day Basel reference thresholds are: Green ≤ 4, Yellow ≤ 9, Red ≥ 10.

---

## 3. Window-Size Sensitivity

| Window | Observations | Expected | Observed | Breach rate | Kupiec LR | p-value | Reject H₀ |
|--------|-------------|---------|---------|------------|----------|---------|----------|
| 20 | 232 | 2.3 | — | — | — | — | Yes |
| 40 | 212 | 2.1 | — | — | — | — | Yes |
| **60** | **192** | **1.9** | **7** | **3.65%** | **8.09** | **0.0045** | **Yes** |
| 90 | 162 | 1.6 | — | — | — | **0.113** | **No** |
| 120 | 132 | 1.3 | — | — | — | — | Yes |

The model passes Kupiec only at W = 90 (p = 0.113). All other windows fail. The verdict is therefore not robust to window selection — the W = 90 pass is an artefact of a shorter backtest period that excludes the Jul 2025 breaches, not evidence of a well-calibrated model.

---

## 4. P&L Attribution — Risk Analysis

All figures are weighted P&L contributions in **basis points (bps)** of portfolio value (1 bps = 0.01%). Portfolio-level totals are quoted in **%** to match the VaR and return series.

### 4.1 Cross-Date Structural Findings

**UBSG recurring exposure.**  UBSG ranks among the top two detractors on five of seven breach dates (−3.0 bps to −32.5 bps). Contribution data alone cannot distinguish structural overweight from high idiosyncratic volatility — marginal VaR decomposition required.

**Sovereign hedge — conditionally effective, two distinct failure modes.**  Effective on Sep 22 (+42.3 bps), Oct 16 (+6.3 bps), and Nov 11 (+17.6 bps). Failed on Jul 7 (rates-driven; −11.2 bps, compounding the loss) and dormant on Oct 1 (equity-idiosyncratic; essentially zero). A single hedge ratio calibrated on full-sample correlation overstates tail diversification benefit.

**Swiss pharma concentration (NOVN, ROG).**  Top two equity detractors on four of five cluster dates. NOVN on Nov 11 (−45.4 bps) is an outlier relative to its own history — consistent with a stock-specific catalyst being strongly indicated. Both names warrant single-issuer limit review.

**IG corporate bonds diverge from sovereigns.**  On Oct 16, sovereigns rallied (+6.3 bps) while NESN_CORP (−5.4 bps), UBSG_CORP (−4.9 bps), and NOVN_CORP (−4.5 bps) were simultaneously negative — a direct signal of credit spread widening. Sovereign and IG credit offsets should not be aggregated as a single fixed-income hedge.

### 4.2 Date-by-Date Analysis

**Jul 7 — Rates-inflected risk-off; hedge additive to loss.**  All 18 instruments negative including short-duration sovereigns. Bond allocation compounded the loss (−11.2 bps). Consistent with a parallel rates sell-off where rising yields pressure both equities and bond marks simultaneously. Top detractors: UBSG −10.1, SIE −8.1, NOVN −7.9, ROG −7.7 bps. Portfolio loss: −0.70%. *Hedge-failure mode 1: duration is source of risk, not mitigant.*

**Jul 15 — Broad equity de-risking; early flight-to-quality bid.**  Sovereigns turned positive (+7.4 bps aggregate; CHGOV_10Y +2.9 bps). Loss spread across NOVN (−14.6 bps), ASML (−12.1 bps), SREN (−8.9 bps), NESN (−6.9 bps) — spanning both growth and defensive names, confirming broad de-risking rather than sector rotation. Portfolio loss: −0.65%; sovereign offset: +7.4 bps.

**Sep 22 — Textbook risk-off; hedge active but undersized.**  Sovereigns strongly bid (CHGOV_10Y +18.7, CHGOV_2Y +6.6, CHGOV_5Y +7.5, DBRGOV_5Y +5.7, FRGOV_7Y +3.8 bps; total +42.3 bps). Loss dominated by systematic large-cap Swiss equity beta; no single-name outlier. Gross equity loss (≈−165 bps) overwhelmed the hedge — a sizing problem, not a hedge-effectiveness problem. Portfolio loss: −1.24%; sovereign offset: +42.3 bps.

**Oct 1 — Equity-idiosyncratic shock; hedge dormant.**  Sovereigns near-zero (total +0.1 bps). Curve lightly steepened (CHGOV_2Y −0.6, CHGOV_10Y +0.2 bps) — flight-to-quality episodes bull-flatten; a steepener confirms no macro fear catalyst was present. Top detractors: UBSG −32.5, ROG −28.2, ABBN −23.4, ASML −22.8 bps. Portfolio loss: −2.00%. *Hedge-failure mode 2: flight-to-quality channel never activated.*

**Oct 16 — Tech and pharma drawdown; credit spreads widen.**  ASML −32.3, NOVN −31.8, NESN −31.6, ROG −29.2 bps. Sovereigns +6.3 bps but IG corporates simultaneously negative (see above). The rolling VaR estimate stood at 1.55% on this date versus a realised loss of 2.50% — an overshoot of 95 bps. The 60-day estimation window had begun incorporating September's elevated vol but had not yet caught up with the pace of realised losses. Portfolio loss: −2.50%; sovereign offset: +6.3 bps.

**Nov 11 — Peak stress; pharma catalyst strongly indicated.**  NOVN −45.4 bps is the largest single-instrument contribution in the entire breach set, well above its own prior peak (−31.8 bps on Oct 16). ROG −39.8 bps follows — a sector-level catalyst is strongly indicated, though single-name confirmation requires additional data (option skew, news flow). Sovereign (+17.6 bps) and IG corporate (+2.9 bps) bonds provided +20.5 bps combined offset, dwarfed by equity losses of approximately −287.6 bps. Portfolio loss: −2.65%.

**Feb 20, 2026 — Systematic, low-idiosyncratic breach.**  Losses evenly distributed (ABBN −17.7, UBSG −16.2, NESN −15.4, ASML −14.0 bps); no single-name outlier. Small sovereign offset (+4.2 bps). Consistent with a model-calibrated tail draw — no structural signal. Portfolio loss: −1.13%.

---

## 5. Model Validation Summary

### 5.1 Test Results

| Test | Statistic | p-value | Result | MRM Tier |
|------|-----------|---------|--------|----------|
| Kupiec POF — flat HS (99%, 192d) | LR = 8.09 | 0.0045 | **FAIL** | 1 — Escalate |
| Kupiec POF — EWMA HS (λ=0.94, 192d) | LR = 5.60 | 0.0179 | **FAIL** | 1 — Escalate |
| Christoffersen independence (lag-1) | LR = 0.53 | 0.4655 | **PASS** | — |
| Conditional Coverage (CC) | LR = 8.62 | 0.0134 | **FAIL** | 1 — Escalate |
| ES coverage ratio (flat HS) | 1.25× | CI [1.10, 1.47] | **FAIL** — CI entirely above 1.0 | 1 — Escalate |
| Basel Traffic Light — flat HS | 7 breaches / 192d | — | **YELLOW** (×3.62) | 2 — Capital add-on |
| Basel Traffic Light — EWMA HS | 6 breaches / 192d | — | **YELLOW** (×3.51) | 2 — Capital add-on |

### 5.2 MRM Escalation Framework

| Finding | Severity | Required Action |
|---------|----------|-----------------|
| Kupiec FAIL (p < 0.05) | High | Immediate MRM notification; model placed under enhanced monitoring |
| CC FAIL | High | Model recalibration; consider moving to stressed ES (FRTB) |
| ES coverage ratio CI > 1.0 | High | ES model underestimates tail severity; stressed ES supplement required |
| Yellow traffic light | Medium | Capital multiplier add-on; quarterly revalidation |
| Red traffic light | Critical | Automatic model suspension; senior risk officer sign-off required |

### 5.3 Key Findings

1. **Both flat HS and EWMA HS fail Kupiec.**  EWMA reduces breaches from 7 to 6 and improves the p-value from 0.0045 to 0.0179, but remains below the 5% threshold. The Jul 7 and Jul 15 breaches — set in a calm, low-vol regime with a tight VaR — are structurally unaffected by EWMA rescaling. The failure is driven by the Sep–Nov cluster, which EWMA partially absorbs but cannot fully resolve within a 60-day window.

2. **ES systematically underestimates tail severity by ~25%.**  The coverage ratio of 1.25× (95% CI [1.10, 1.47]) is entirely above 1.0. The Sep–Nov cluster generates losses 30–100% above the ES estimate because the model is calibrated on a calm window — the regime-lag failure seen in Kupiec also propagates to the ES level.

3. **Christoffersen lag-1 passes, but the CC test fails — and the distinction matters.**  n11 = 0: no two breach days were ever consecutive. The CC failure (LR = 8.62, p = 0.013) is entirely driven by the Kupiec frequency component. The Sep–Nov cluster at multi-week scale is invisible to the lag-1 test; a duration-based test (Christoffersen & Pelletier 2004) is needed to formally capture within-quarter clustering, but is underpowered at n = 6 durations.

4. **Both models land in the Basel Yellow zone.**  At 7 and 6 breaches respectively, both incur a capital multiplier add-on. The flat HS multiplier is ×3.62; EWMA is ×3.51. Neither would pass a regulator's internal model approval review in this state.

---

## 6. Implications for Risk Management

| Finding | Action |
|---------|--------|
| UBSG recurring exposure | Marginal / component VaR decomposition; review single-name concentration limit |
| NOVN / ROG concentration | Independent pharma stress test; consider sector VaR sub-limit |
| Hedge-failure mode 1 (Jul 7) | Review duration contribution to VaR; evaluate curve hedge for rates-shock scenarios |
| Hedge-failure mode 2 (Oct 1) | Ensure equity-only stress scenario is covered independently of macro-fear channel |
| Sovereign / IG credit divergence | Model offsets separately; do not aggregate as a single fixed-income hedge |
| Sep–Nov cluster (4 breaches) | Christoffersen lag-1 p=0.47 (PASS); CP duration p=0.74 (PASS, underpowered n=6); CC p=0.013 (FAIL — Kupiec-driven). Cluster at multi-week scale; implement 10-day rolling breach-rate monitor |
| Estimation window sensitivity | Kupiec passes at W=90 (p=0.113); fails at W=20, 40, 60, and 120. Consider adaptive window selection or regime-conditional window sizing |
| ES under-coverage (1.25×) | Add stressed ES overlay using a dedicated stress period (GFC 2008–09 or Mar 2020); re-test ES coverage after inclusion |
| 60-day window lag | EWMA reduces Kupiec LR by 2.5 points but does not resolve the root-cause regime-lag or heavy-tails bias; evaluate GARCH(1,1) as an alternative |

---

## 7. Recommended Model Enhancements

| Priority | Enhancement | Expected Impact |
|----------|-------------|-----------------|
| P1 | Increase EWMA window or use a two-component λ mix (0.94 calm / 0.97 stressed) | Reduce Jul calm-regime false breaches while retaining fast stress response |
| P1 | Add stressed ES overlay — include a dedicated stress period (e.g. GFC 2008–09, Mar 2020) | Directly addresses 1.25× ES under-coverage |
| P2 | Implement Christoffersen–Pelletier (2004) duration test at 3–4 year backtest horizon | Detects multi-week clustering invisible to lag-1 independence test |
| P2 | Extend backtest to 250-day window when sufficient history is available | Enables direct Basel traffic light comparison without threshold scaling |
| P2 | Implement GARCH(1,1) vol-scaling as alternative to EWMA | More flexible heteroskedasticity model; benchmark LR against EWMA |
| P3 | Implement 97.5% ES backtest (FRTB primary metric) | Aligns with FRTB IMA requirements for internal model approval |
| P3 | Single-name concentration review (NOVN, ROG, UBSG) | Reduces idiosyncratic risk contribution; improves independence test outcome |

---

## 8. Document Control

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2026-04-18 | Martin Diergardt | Initial version — results from `notebooks/backtest_explained.ipynb` |
