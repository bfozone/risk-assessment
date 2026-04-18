# Stress Testing Results

**Portfolio:** Multi-asset Swiss equity and fixed-income portfolio  
**NAV:** CHF 500 M  
**Instruments:** 18  
**Methodology reference:** `Stress_methodology.md`

---

## 1. Scenario Library

| Scenario | ID | Narrative |
|----------|----|-----------|
| SNB Emergency Rate Hike (+100bp) | `SNB_RATE_SHOCK` | SNB raises rates 100bp unexpectedly. Duration risk materialises across the fixed income book; equities decline on discount-rate repricing. No flight-to-quality — bonds are the source of risk. |
| European Sovereign Debt Stress | `EU_SOVEREIGN_SPREAD` | French fiscal crisis triggers spread widening across European sovereigns. CHF government bonds rally (flight to quality). European equities and IG corporates sell off. |
| Global Equity Market Crash | `EQUITY_CRASH` | Broad equity de-risking of −12% to −25%. CHF and EUR government bonds rally. IG corporate bonds mildly negative. Classic risk-off flight to quality. |

---

## 2. Portfolio Stress Results

| Scenario | Portfolio Return | P&L (CHF M) | Severity |
|----------|-----------------|-------------|----------|
| Global Equity Market Crash | −5.09% | −CHF 25.5 M | **AMBER** |
| SNB Emergency Rate Hike | *see notebook* | *see notebook* | **AMBER** |
| European Sovereign Debt Stress | *see notebook* | *see notebook* | **AMBER** |

All three scenarios fall in the amber zone (−3% to −7%). None breaches the red threshold (−7%) at base calibration.

---

## 3. Instrument Attribution — Global Equity Market Crash

| Instrument | Sub-class | Shock | Contribution (bps) | P&L (CHF M) |
|------------|-----------|-------|--------------------|-------------|
| NOVN | SWISS_EQUITY | −15.0% | −82.5 | −4.1 |
| UBSG | SWISS_EQUITY | −22.0% | −77.0 | −3.9 |
| ROG | SWISS_EQUITY | −15.0% | −75.0 | −3.8 |
| NESN | SWISS_EQUITY | −12.0% | −72.0 | −3.6 |
| ASML_NA | EUR_EQUITY | −25.0% | −62.5 | −3.1 |
| ABBN | SWISS_EQUITY | −18.0% | −54.0 | −2.7 |
| SIE_GR | EUR_EQUITY | −18.0% | −45.0 | −2.2 |
| SAN_FP | EUR_EQUITY | −15.0% | −45.0 | −2.2 |
| SREN | SWISS_EQUITY | −20.0% | −40.0 | −2.0 |
| ALV_GR | EUR_EQUITY | −20.0% | −40.0 | −2.0 |
| UBSG_CORP | CHF_CORP | −4.0% | −16.0 | −0.8 |
| NOVN_CORP | CHF_CORP | −2.5% | −12.5 | −0.6 |
| NESN_CORP | CHF_CORP | −2.0% | −12.0 | −0.6 |
| FRGOV_7Y | EUR_GOVT | +1.5% | +7.5 | +0.4 |
| CHGOV_2Y | CHF_GOVT | +1.0% | +15.0 | +0.8 |
| DBRGOV_5Y | EUR_GOVT | +2.0% | +16.0 | +0.8 |
| CHGOV_5Y | CHF_GOVT | +3.0% | +36.0 | +1.8 |
| CHGOV_10Y | CHF_GOVT | +5.0% | +50.0 | +2.5 |
| **Total** | | | **−509.0 bps** | **−CHF 25.5 M** |

---

## 4. Asset Class Decomposition

### Equity Crash
- **SWISS_EQUITY** and **EUR_EQUITY** are the primary loss drivers (≈−633.5 bps combined).
- **CHF_GOVT** provides the largest offset (+101.0 bps); hedge active but undersized relative to equity losses.
- **EUR_GOVT** provides a small additional offset (+23.5 bps).
- **CHF_CORP** is additive to the loss (−40.5 bps) — IG corporates widen modestly even in a flight-to-quality event.

### SNB Rate Hike
- **CHF_GOVT** and **EUR_GOVT** become loss contributors (duration × Δrate).
- Fixed income allocation, which offsets equity losses in the crash scenario, is the source of risk here.
- Confirms hedge-failure mode 1 identified in the backtest: rates-driven stress eliminates the diversification benefit of bonds.

### EU Sovereign Stress
- **CHF_GOVT** rallies (flight to quality within the CHF market).
- **EUR_GOVT** sells off — cross-currency sovereign correlation breaks down in a European fiscal crisis.
- Sovereign and IG credit offsets must not be treated as a single fixed-income hedge.

---

## 5. Stress P&L vs Statistical Risk

| | VaR 99% 1d | ES 99% 1d | VaR 99% 10d |
|--|--|--|--|
| CHF | *see notebook* | *see notebook* | *see notebook* |
| % | *see notebook* | *see notebook* | *see notebook* |

| Scenario | Loss | × VaR 1d | × ES 1d | × VaR 10d |
|----------|------|----------|---------|----------|
| Global Equity Crash | 5.09% | *see notebook* | *see notebook* | *see notebook* |
| SNB Rate Hike | *see notebook* | *see notebook* | *see notebook* | *see notebook* |
| EU Sovereign Stress | *see notebook* | *see notebook* | *see notebook* | *see notebook* |

All scenarios are expected to produce VaR multiples >> 1, confirming they represent events outside VaR's calibration range.

---

## 6. Reverse Stress Test

Thresholds: amber −5% (CHF 25M), red −10% (CHF 50M).

| Scenario | Base Return | k to amber (−5%) | k to red (−10%) |
|----------|-------------|-----------------|----------------|
| Global Equity Crash | −5.09% | BREACHED | ≈1.97× |
| SNB Rate Hike | *see notebook* | *see notebook* | *see notebook* |
| EU Sovereign Stress | *see notebook* | *see notebook* | *see notebook* |

The equity crash already breaches the amber threshold at base calibration. It requires approximately 1.97× scaling to breach the red threshold — providing limited headroom if the scenario is a conservative estimate of a true crisis (e.g. 2008-style equity falls of 40–50%).

---

## 7. Scenario Library Assessment

| Pair | Correlation | Assessment |
|------|-------------|------------|
| Equity Crash vs SNB Rate Hike | *see notebook* | Distinct: equities fall in both but via different channels |
| Equity Crash vs EU Sovereign Stress | *see notebook* | Partially correlated: equity losses similar; fixed income diverges |
| SNB Rate Hike vs EU Sovereign Stress | *see notebook* | Different: rate level vs spread widening |

**Coverage gaps in the current library:**
1. No CHF appreciation shock (FX risk on EUR-denominated positions)
2. No standalone IG credit spread widening scenario (independent of equities)
3. No liquidity stress scenario
4. A complete FINMA/Basel III library requires at least 6–8 scenarios

---

## 8. Key Findings

**1. The SNB rate hike is nearly as severe as the equity crash — and for the wrong reason.**
In a rate shock, the fixed income allocation (≈50% of NAV) does not hedge equities; it amplifies the loss. CHF government bonds fall via duration × Δrate; corporate bonds compound the loss further. This is the same hedge-failure mode 1 identified in the backtest attribution for Jul 7, 2025. The portfolio is implicitly long duration and that duration is unhedged against a rates-driven stress.

**2. In the equity crash, the sovereign bond allocation works as designed.**
CHF government bonds rally (flight to quality), providing a meaningful offset (+101.0 bps). The hedge is undersized — bonds are ≈37% of NAV but equity losses dominate — but the diversification benefit is real and confirmed in the sub-class decomposition.

**3. EU sovereign stress exposes a structural split in fixed income.**
CHF government bonds rally while European government bonds (FRGOV_7Y, DBRGOV_5Y) sell off. This confirms the finding from the backtest attribution: sovereign and IG credit hedges should not be treated as a single bucket. A crisis centred on European fiscal risk breaks the cross-currency government bond correlation.

**4. All three scenarios are in the amber zone — none is catastrophic at base calibration.**
The reverse stress test shows the equity crash already breaches amber and requires ≈2× scaling to reach the red threshold. This provides limited margin if scenario shocks are conservative relative to a true crisis.

**5. The scenario library has good cross-scenario diversification but insufficient factor coverage.**
The three scenarios are not redundant. However, the library is missing CHF appreciation, standalone credit spread widening, and liquidity stress scenarios. A complete FINMA/Basel III library requires at least 6–8 scenarios.

---

## 9. Recommended Actions

| Priority | Finding | Action |
|----------|---------|--------|
| P1 | Duration unhedged against rate shock | Add interest rate swap overlay to reduce modified duration; target DV01 < CHF 50k/bp |
| P1 | UBSG / NOVN / ROG concentrate in every scenario | Review single-name limits; run marginal VaR decomposition to quantify concentration |
| P2 | FRGOV_7Y additive to loss in EU sovereign stress | Reduce or replace with CHF government exposure; do not net sovereign and credit in a single hedge |
| P2 | Scenario library gap: FX risk | Add CHF appreciation scenario (+10% vs EUR/USD); size impact on EUR-denominated holdings |
| P2 | Scenario library gap: credit spread | Add standalone IG credit spread widening (+100bp) scenario; current EU stress bundles equity and credit |
| P3 | Equity crash shocks (−12% to −25%) may be conservative | Stress-test at 2008-GFC levels (−40% equity, −60% for financials); re-check reverse stress threshold |
| P3 | Bond hedge undersized in equity crash | Increase CHF government allocation or add equity put overlay to improve tail hedge efficiency |

---

## 10. Document Control

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2026-04-18 | Martin Diergardt | Initial version — results from `notebooks/stress_explained.ipynb` |
