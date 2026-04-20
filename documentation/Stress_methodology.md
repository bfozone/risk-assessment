# Stress Testing — Methodology

**Notebook:** `notebooks/stress_explained.ipynb`
**Results:** `documentation/Stress_results.md`
**Companion document:** `methodology.md` (VaR/ES backtesting) — stress testing addresses tail events beyond the confidence level tested there.

---

## 1. Scope

This document specifies the stress-testing methodology applied in the accompanying notebook. It covers the construction, computation, and interpretation of scenario-based stress tests for a multi-asset portfolio.

**Implemented in the notebook:**

- Scenario-based stress P&L computation (linear shock model)
- Instrument-level attribution and asset-class decomposition
- Stress P&L vs statistical risk (VaR / ES multiples)
- Scenario library correlation and risk factor coverage

**Documented as outlook** (not implemented; see §6):

- Scenario-to-limit distance (severity ranking against defined loss limits)
- Sensitivity analysis (uniform shock scaling)
- Factor-space reverse stress test (BCBS 2009 sense)

**Out of scope** (addressed separately):

- Regulatory applicability and entity-specific requirements
- Severity classification thresholds and escalation triggers (defined by the institution's risk appetite framework)
- Scenario governance — proposal, approval, library refresh, escalation
- Scenario library construction criteria — admissibility, severity calibration, plausibility
- Hedging treatment under stress — basis risk, hedge effectiveness, counterparty risk
- Model validation and independent review
- Liquidity stress testing, enterprise stress testing, climate stress testing

---

## 2. Stress Testing vs VaR

VaR and stress testing answer different questions and should be read as complements, not substitutes.

| Dimension | VaR | Stress Testing |
| --- | --- | --- |
| Basis | Statistical (historical returns) | Scenario-driven (specified shocks) |
| Confidence | 99% / 97.5% | N/A — losses are point estimates |
| Horizon | 1-day | Instantaneous shock |
| Tail coverage | Up to confidence threshold | Designed for events beyond VaR |
| Key weakness | Backward-looking; regime-blind | Scenarios may not materialize |

VaR quantifies risk *inside* the statistical confidence region. Stress testing quantifies risk *outside* it — the severe-but-plausible events that VaR is not designed to capture. A complete risk picture needs both.

---

## 3. Scenario Construction

Each scenario specifies a `shock_return` per instrument, applied as an instantaneous single-period mark-to-market shock. No time-series dynamics are modelled.

**Scenario types:**

| Type | Description | Current scenarios |
| --- | --- | --- |
| Historical | Replays a documented crisis | Not in current dataset |
| Hypothetical | Plausible-but-unobserved shocks | SNB rate hike, EU sovereign, equity crash |
| Reverse | Identifies factor combinations producing a specified loss | Not implemented (outlook — §6) |

Historical scenarios anchor the library to events that have actually occurred. Hypothetical scenarios extend coverage to factor combinations not seen historically — critical because stress testing is meant to cover the unobserved, not just replay the observed. A well-constructed library should include both.

### 3.1 Current scenario library

The current library contains three hypothetical scenarios:

| Scenario | Primary risk factors stressed |
| --- | --- |
| SNB Emergency Rate Hike (+100bp) | Rates (level), bank/insurer equity |
| European Sovereign Debt Stress | EU credit spreads, EUR equity, flight-to-quality CHF govvies |
| Global Equity Market Crash | Equity beta (broad), mild credit widening, flight-to-quality |

All three scenarios produce meaningful losses in the equity sleeves (SWISS\_EQUITY, EUR\_EQUITY) and partial offsets from CHF government bonds. The shock-matrix correlation analysis in §7 confirms this: the three scenarios share structural similarity in their equity-down / govvie-up pattern, covering "equities down" in three flavours rather than spanning the risk-factor space. No scenario stresses FX, credit spreads independently of rates, or tests a correlated sell-off across all asset classes simultaneously.

A three-scenario library is a minimum viable starting point. For a multi-asset portfolio spanning rates, credit, equity, and FX, a serious library requires at minimum five to eight scenarios covering distinct regions of the factor space.

### 3.2 Recommended scenario library extensions

The following five scenario types are absent from the current library. Each targets a distinct risk factor or factor combination and would materially improve coverage.

#### 1. Credit spread widening (independent of rates)

A pure credit event — corporate spreads widen 150–300 bps across ratings, with little or no move in risk-free rates or equity. This stresses CHF\_CORP and EUR corporate credit without the equity-down channel that dominates the existing scenarios. It is the primary uncovered factor for the CHF\_CORP and EUR corporate credit sleeves, which currently receive only mild shocks (−2% to −4%) under the equity crash scenario.

#### 2. FX shock (CHF/EUR and USD/CHF)

A CHF appreciation of 5–10% against EUR and USD, analogous to the January 2015 SNB floor removal or March 2022 risk-off episodes. EUR\_EQUITY and EUR\_GOVT instruments are denominated in EUR; CHF/EUR moves directly affect their CHF mark-to-market value. The current scenarios specify no FX shocks — EUR-denominated positions are implicitly treated as fully hedged, which overstates diversification for an unhedged or partially hedged portfolio.

#### 3. Liquidity crunch (correlated sell-off)

A regime in which all risky asset classes sell off simultaneously and the usual flight-to-quality offset from government bonds fails. The Jul 7 2025 VaR breach documented in the backtest analysis is an example: a broad risk-off episode where even govvies cheapened as investors sought cash. In this scenario, correlation assumptions break down and the diversification benefit embedded in the component VaR framework does not materialise. Under the current three scenarios, government bonds always provide a partial offset; this scenario tests what happens when they do not.

#### 4. Inflation shock (rates up, equities down)

A stagflationary episode in which rates rise (bond prices fall via duration) while equities also sell off (valuation compression, margin pressure). The SNB rate hike scenario partially captures this but from a monetary-policy-defence mechanism — equities decline through the financial-sector channel, not the broad earnings-compression channel. An independent inflation scenario would apply a larger, more uniform rate shock across the curve and a simultaneous equity decline across all sectors, testing whether the portfolio's rate-sensitivity and equity-beta add rather than offset.

#### 5. Historical replays

At least two historical scenarios should be added to anchor the library to observed events:

- **2008 Q4 (Lehman):** broad equity collapse (−40% over the quarter), credit spreads to multi-decade highs, funding market seizure. Representative of the correlated tail event the library is missing.
- **March 2020 (COVID crash):** sharp equity drawdown (−30% peak-to-trough over three weeks), initial credit widening, followed by central bank intervention. Notable because the sell-off and recovery were unusually fast, testing liquidity assumptions.

Historical scenarios have two advantages over hypothetical ones: (a) the factor moves are internally consistent by construction — they actually co-occurred — and (b) they provide a benchmark against which to calibrate the severity of hypothetical scenarios. The current library has no historical scenarios (see §3 type table above).

---

## 4. P&L Computation

Portfolio return under scenario $s$:

$$\text{Portfolio return}_s = \sum_i w_i \cdot \text{shock}_{i,s}$$

where $w_i$ is the **portfolio weight** of instrument $i$ (dimensionless, $\sum_i w_i = 1$) and $\text{shock}_{i,s}$ is the scenario return for that instrument.

Absolute portfolio P&L:

$$\text{P\&L}_s = \text{NAV} \times \text{Portfolio return}_s$$

Instrument contribution in basis points:

$$\text{Contribution}_{i,s} = w_i \cdot \text{shock}_{i,s} \times 10{,}000 \;\text{bps}$$

### 4.1 Linearity assumption and its limits

The model is linear: no convexity, no second-order effects, no delta / gamma adjustment. This is a first-order approximation.

For portfolios with material optionality, duration, or convexity exposure, a linear shock model **understates large-move sensitivities**. Concretely:

- **Bonds** with meaningful duration experience larger price moves under a big rate shock than a linear model predicts; negative convexity in callable bonds amplifies this further on the downside.
- **Options** have non-linear payoffs by construction; delta alone misses gamma and vega effects, which dominate at large moves.
- **Structured products** with path-dependent or barrier features are poorly approximated by any single-period linear model.

Where these exposures are material, the linear result should be read as a lower bound on the true stress loss, and supplemented with full-revaluation pricing for the affected positions.

---

## 5. VaR Multiples

Stress losses are benchmarked against statistical risk measures computed from the same portfolio:

$$\text{VaR multiple}_s = \frac{|\text{Stress return}_s|}{\text{VaR}_{99\%,\,1d}}$$

where $\text{VaR}_{99\%,\,1d}$ is the 99% one-day VaR estimated from the full backtest window (as defined in `methodology.md` §6.1).

### 5.1 Interpretation

Stress losses are, by design, events that statistical risk measures fail to anticipate. VaR multiples are useful as a sanity check on scenario severity — *"is this scenario a routine tail event or a genuine stress?"* — but should not be read as a tight benchmark. A VaR multiple of 3× does not mean the scenario is three times more severe than the model predicts; it means the scenario is in a region where the model is not calibrated.

VaR multiples above 4–5× typically indicate scenarios that belong in the stress-test framework rather than the statistical-risk framework.

---

## 6. Outlook: extensions not currently implemented

Three extensions to the framework are documented here but not implemented. Each is deferred for a different reason — some wait on defined loss limits, some on additional infrastructure — and the implementation path for each is distinct.

### 6.1 Scenario-to-limit distance

For a defined loss limit $L$ and a scenario return $r_s$ (both negative for scenarios of interest), the scenario severity multiple is $k_s = L / r_s$: the factor by which the scenario must be amplified to reach the limit. $k_s \leq 1$ means the scenario already breaches. This produces a severity ranking of the scenario library against a fixed reference.

**Why not implemented.** The loss limits are defined externally in the institution's risk appetite framework. Once confirmed, the computation is trivial.

**Limitation.** This is not a reverse stress test in the BCBS (2009) sense — it searches only within the existing library along the single dimension of uniform scaling. For a genuine reverse stress test, see §6.3.

### 6.2 Sensitivity analysis

Sensitivity analysis answers *"how does portfolio stress loss change with the severity or composition of the shocks?"* The design space is broad and the simplest variants are often not the most informative:

- **Uniform scaling.** Multiply all shocks in a scenario by a common factor $k$ and trace the loss profile. Because the shock model is linear (§4.1), this adds no information beyond the base result — it is a recomputation of the same scenario at different severities.
- **Single-factor shifts.** Hold the base scenario fixed and vary one risk-factor dimension (e.g. the rates-shock component, the equity-shock component) to isolate that factor's contribution to the total loss.
- **Non-uniform scaling within a scenario.** Scale different asset classes or risk factors at different rates to explore which combination drives the loss (e.g. amplify the credit component while holding rates fixed).
- **Stress-of-stress.** Apply an incremental shock on top of the base scenario to test robustness of hedges and of the scenario assumptions themselves.

**Why not implemented.** Each of these variants requires either defined loss limits (to identify meaningful crossings) or a factor-level representation of the portfolio (which the current notebook does not have). The uniform-scaling variant is the simplest but also the least useful, given linearity.

**Recommendation when implemented.** Prefer single-factor and non-uniform variants over uniform scaling. Uniform scaling is essentially a visualization of §6.1 and carries no additional information.

### 6.3 Factor-space reverse stress test

A full reverse stress test inverts the usual direction: *"given this loss level, what combination of market moves would produce it?"* This can surface vulnerabilities the scenario library does not contain. Two standard approaches:

- **Optimization.** Find the closest (least implausible) factor combination that produces loss $\geq L$ — typically minimizing Mahalanobis distance under the estimated factor covariance, or likelihood under an assumed joint distribution.
- **Simulation.** Monte Carlo the factor distribution, filter for tail outcomes, and examine which factor moves dominate the filtered set.

**Why not implemented.** Requires a risk-factor model (covariance or joint distribution), full-revaluation pricing beyond the linear shock approximation, and a longer return history to estimate tail dependence reliably — none of which are in place.

**When to implement.** When (a) the scenario library is large enough that factor-coverage gaps are a real concern, (b) a factor model is available from adjacent risk infrastructure, or (c) governance or regulatory review specifically requests it.

---

## 7. Scenario Correlation

Correlation is computed from the $N_{\text{instruments}} \times N_{\text{scenarios}}$ shock matrix. Pairwise correlations near +1.0 indicate two scenarios stress similar instruments in similar directions; correlations near 0 indicate orthogonal coverage.

**Design principle:** a well-constructed library should have low pairwise correlations — distinct factor coverage across rates, credit, equity, and FX.

### 7.1 Limitation

This metric captures **instrument-level overlap** between scenarios, which is a proxy for risk-factor coverage but not identical to it. Two scenarios driven by the same underlying risk factor may still show low shock-matrix correlation if they hit different instruments. For example, an "EU sovereign crisis" scenario stressing peripheral govvies and a "banking crisis" scenario stressing bank equities are both credit / risk-off events loading on the same underlying factor, but the instrument overlap is low and they will appear orthogonal in the shock-matrix correlation.

A more complete analysis maps scenarios to an explicit risk-factor taxonomy (rates level, rates curve, credit spreads by rating, equity beta, FX, commodity) and checks coverage at the factor level rather than the instrument level. Factor-level analysis is not implemented in the current notebook; the shock-matrix correlation is a reasonable first pass but should be read with this limitation in mind.

---

## 8. Conventions

| Quantity | Unit | Example |
| --- | --- | --- |
| Portfolio return, shock_return | % | −5.09% |
| Instrument P&L contributions | bps | −82.5 bps |
| Absolute P&L | CHF M | −CHF 25.5 M |
| VaR / ES multiples | × | 4.1× |

**Conversion:** 1 bps = 0.01%. To convert instrument contributions (bps) to portfolio return (%): divide by 100.

**Sign convention:** returns and P&L figures are signed. Losses are negative (e.g., −5.09%, −CHF 10M). Absolute values are used only in ratios where the denominator is already a magnitude (e.g., VaR multiples).

---

## 9. Glossary

- **Hypothetical scenario:** a plausible-but-unobserved shock specification, in contrast to a historical scenario that replays a documented crisis.
- **Reverse stress test:** identification of the factor combination that would produce a specified loss level. In the strict BCBS (2009) sense, this requires searching over the risk-factor space (see §6.3). A simplified scenario-to-limit distance computation is described in §6.1. Neither is currently implemented in the notebook.
- **Scenario:** a specification of shock returns for each instrument in the portfolio, representing a hypothesized market event.
- **Sensitivity analysis:** evaluation of portfolio P&L under uniform scaling of all shocks in a scenario.
- **Shock:** the return assigned to an instrument under a scenario.
- **VaR multiple:** stress loss divided by 99% one-day VaR; a benchmark indicating how far into the tail a scenario sits.

---

## 10. References

- Basel Committee on Banking Supervision (2009). *Principles for sound stress testing practices and supervision.*

### Document Control

| Version | Date | Author | Change |
| --- | --- | --- | --- |
| 1.0 | 2026-04-18 | Martin Diergardt | Initial version |

Methodology updates are tracked here. Scenario library updates are tracked separately in the scenario register.
