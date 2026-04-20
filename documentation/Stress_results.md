# Stress Testing Results

**Portfolio:** Multi-asset Swiss equity and fixed-income portfolio  
**NAV:** CHF 500 M  
**Instruments:** 18  
**Methodology reference:** `Stress_methodology.md`

---

## 1. Scenario Library

| Scenario   | ID  | Narrative   |
| ---------- | --- | ----------- |
| SNB Emergency Rate Hike (+100bp) | `SNB_RATE_SHOCK` | SNB raises rates 100bp unexpectedly. Duration risk materializes across the fixed income book; equities decline on discount-rate repricing. No flight-to-quality — bonds are the source of risk. |
| European Sovereign Debt Stress | `EU_SOVEREIGN_SPREAD` | French fiscal crisis triggers spread widening across European sovereigns. CHF government bonds rally (flight to quality). European equities and IG corporates sell off. |
| Global Equity Market Crash | `EQUITY_CRASH` | Broad equity de-risking of −12% to −25%. CHF and EUR government bonds rally. IG corporate bonds mildly negative. Classic risk-off flight to quality. |

---

## 2. Portfolio Stress Results

| Scenario                        | Portfolio Return | P&L (CHF M)  |
| ------------------------------- | ---------------- | ------------ |
| Global Equity Market Crash      | −5.09%           | −CHF 25.4 M  |
| SNB Emergency Rate Hike         | −4.91%           | −CHF 24.5 M  |
| European Sovereign Debt Stress  | −2.49%           | −CHF 12.4 M  |

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
| **Total** | | | **−509.0 bps** | **−CHF 25.4 M** |

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

| Metric       | VaR 99% 1d | ES 99% 1d | VaR 99% 10d (*) |
| ------------ | ---------- | --------- | --------------- |
| CHF M        | 10.1       | 12.0      | 31.9            |
| %            | 2.02%      | 2.39%     | 6.37%           |

| Scenario                       | Loss   | × VaR 1d | × ES 1d | × VaR 10d (*) |
| ------------------------------ | ------ | -------- | ------- | ------------- |
| Global Equity Market Crash     | 5.09%  | 2.5×     | 2.1×    | 0.8×          |
| SNB Emergency Rate Hike        | 4.91%  | 2.4×     | 2.1×    | 0.8×          |
| European Sovereign Debt Stress | 2.49%  | 1.2×     | 1.0×    | 0.4×          |

Scenarios exceed 1-day VaR by 1.2× to 2.5×, indicating they represent events beyond routine daily tail risk. Against the 10-day Basel horizon, however, all scenarios sit below VaR (0.4× to 0.8×) — the library is at the mild end of the stress spectrum and would benefit from more severe scenarios aligned with historical crisis magnitudes (2008, 2020).

(*) VaR 99% 10d is √10-scaled from the 1-day figure. This assumes i.i.d. daily returns; the return clustering observed in Sep–Nov 2025 (documented in `VaR_backtesting_methodology.md`) inflates the 10-day estimate. Treat × VaR 10d as an upper bound.

---

## 6. Scenario Library Assessment

| Pair | Correlation | Assessment |
| ---- | ----------- | ---------- |
| Equity Crash vs SNB Rate Hike | 0.45 | Moderate overlap — both shock equities, via different channels |
| Equity Crash vs EU Sovereign Stress | 0.74 | High overlap — both are equity-downside regimes with similar instrument impact |
| SNB Rate Hike vs EU Sovereign Stress | 0.15 | Genuinely distinct — covers the rates dimension the others miss |

**Coverage gaps in the current library:**

1. No CHF appreciation shock (FX risk on EUR-denominated positions)
2. No standalone IG credit spread widening scenario (independent of equities)
3. No liquidity stress scenario
4. A complete FINMA/Basel III library requires at least 6–8 scenarios

---

## 7. Key Findings

**1. The SNB rate hike is nearly as severe as the equity crash — and for the wrong reason.**
In a rate shock, the fixed income allocation (≈50% of NAV) does not hedge equities; it amplifies the loss. CHF government bonds fall via duration × Δrate; corporate bonds compound the loss further. This is the same hedge-failure mode 1 identified in the backtest attribution for Jul 7, 2025. The portfolio is implicitly long duration and that duration is unhedged against a rates-driven stress.

**2. In the equity crash, the sovereign bond allocation works as designed.**
CHF government bonds rally (flight to quality), providing a meaningful offset (+101.0 bps). The hedge is undersized — bonds are ≈37% of NAV but equity losses dominate — but the diversification benefit is real and confirmed in the sub-class decomposition.

**3. EU sovereign stress exposes a structural split in fixed income.**
CHF government bonds rally while European government bonds (FRGOV_7Y, DBRGOV_5Y) sell off. This confirms the finding from the backtest attribution: sovereign and IG credit hedges should not be treated as a single bucket. A crisis centred on European fiscal risk breaks the cross-currency government bond correlation.

**4. The scenario library has good cross-scenario diversification but insufficient factor coverage.**
The three scenarios are not redundant. However, the library is missing CHF appreciation, standalone credit spread widening, and liquidity stress scenarios. A complete FINMA/Basel III library requires at least 6–8 scenarios.

---

## 9. Document Control

| Version | Date | Author | Tooling | Change |
| --- | --- | --- | --- | --- |
| 1.0 | 2026-04-18 | Martin Diergardt | Claude Code | Initial version |
| 1.1 | 2026-04-20 | Martin Diergardt | Claude Code | Fill placeholders; fix rounding; correct narratives and correlations |
