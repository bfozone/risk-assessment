# VaR Backtesting — Methodology

This document explains the backtesting methodology applied in the accompanying notebook. It describes what each test does, how it is constructed, and how to interpret its output.

---

## 1. Scope

This document covers the backtesting methods used to check whether a Value-at-Risk (VaR) and Expected Shortfall (ES) model, applied to a multi-asset portfolio, is statistically consistent with realized returns.

**In scope:**

- Rolling out-of-sample backtest construction
- Kupiec POF test (unconditional coverage)
- Christoffersen lag-1 independence test
- Conditional coverage test
- ES coverage ratio (bootstrap diagnostic)
- Flat historical simulation and EWMA volatility estimation
- Basel traffic light framework
- Window-size sensitivity analysis
- Outlook: Christoffersen-Pelletier duration test

---

## 2. Backtest construction

### 2.1 Rolling out-of-sample design

For each day $t$ in the backtest period, the VaR estimate is computed using only the $W$ trading days strictly preceding $t$. The estimate is then compared against the realized portfolio return on day $t$. This enforces the discipline that the model is never evaluated on data it was fitted on.

A **breach** occurs when the realized loss exceeds the VaR estimate:

$$r_t \;<\; -\widehat{\text{VaR}}_t$$

Under a correctly specified VaR at confidence level $\alpha$, the breach indicator sequence $\{I_t\}$ should behave as independent Bernoulli($1-\alpha$) draws. The two properties — correct unconditional frequency and independence across time — are what the tests in sections 3 and 4 examine.

### 2.2 Window selection

The estimation window $W$ is a bias-variance trade-off:

- **Short window (20–40 days):** reacts quickly to volatility changes, noisy VaR estimates, unstable breach counts.
- **Long window (120–250 days):** stable estimates, but slow to reflect regime shifts — produces breach clusters after volatility jumps.

The Basel minimum for historical simulation VaR is 250 days (one trading year). A shorter window (e.g. 60 days) is a common internal choice for faster responsiveness, accepting a higher breach rate in regime shifts. Window selection is made ex-ante and documented; ex-post window tuning biases the backtest toward the desired outcome.

Window sensitivity is reported routinely (see section 6). If a model passes at one window and fails at adjacent windows, the verdict is not robust, which is itself diagnostic information.

### 2.3 Confidence level

Under Basel II/III, 99% VaR is the regulatory benchmark for market-risk internal models. Under FRTB, 97.5% ES replaces 99% VaR as the primary risk measure. The notebook reports both 99% VaR (because the traffic-light framework in section 5 requires it) and 97.5% ES coverage (for continuity with FRTB).

### 2.4 Test philosophy

A VaR model makes two distinct claims simultaneously:

- **Unconditional coverage:** the proportion of breaches over the backtest period equals $1-\alpha$. With 99% VaR over 250 days, the expected number of breaches is 2.5.
- **Independence:** breaches do not cluster in time. A breach on day $t$ should not be informative about whether day $t+k$ will also be a breach, for any $k$.

A model can fail on either dimension or both. The tests in section 3 and section4 are designed to separate these failure modes so that, when a model fails, the source of failure is identifiable.

---

## 3. Kupiec POF test (unconditional coverage)

### 3.1 Purpose

Tests whether the observed breach rate is statistically consistent with the model's claimed confidence level. Introduced by Kupiec (1995) as the *Proportion of Failures* test.

### 3.2 Intuition

Under a correctly specified 99% VaR, each day is an independent Bernoulli(0.01) trial. The total breach count over $T$ days is therefore Binomial($T$, 0.01). Kupiec is a likelihood-ratio comparison between the null Binomial($T$, $1-\alpha$) and the unrestricted Binomial($T$, $\hat{p}$), where $\hat{p}$ is the observed rate.

### 3.3 Test statistic

Let $T$ = number of observation days, $N$ = number of breaches, $p_0 = 1-\alpha$ (expected breach probability), and $\hat{p} = N/T$ (observed rate). The likelihood-ratio statistic is:

$$\text{LR}_{\text{POF}} \;=\; 2 \left[\, N \ln\frac{\hat{p}}{p_0} \;+\; (T-N) \ln\frac{1-\hat{p}}{1-p_0} \,\right]$$

Under $H_0$ (model is correctly calibrated), $\text{LR}_{\text{POF}} \sim \chi^2(1)$. At the 5% significance level the critical value is 3.84. Reject $H_0$ if $\text{LR}_{\text{POF}} > 3.84$, equivalently $p$-value < 0.05.

### 3.4 Interpretation

- **Reject with too many breaches:** model underestimates risk. Capital implications.
- **Reject with too few breaches:** model is over-conservative. Less serious for regulatory purposes but indicates inefficient capital allocation.
- **Do not reject:** frequency is consistent with the claim. This does not establish that the model is correct — only that the frequency property is not falsified at this sample size.

### 3.5 Limitations

Kupiec addresses frequency only. A model that produces the correct number of breaches, all concentrated in a single stress week, passes Kupiec. The independence test in section4 addresses this gap.

Power is low at short sample periods. At 99% VaR with a one-year backtest, the expected breach count is 2.5. Distinguishing between a true 1% rate and a true 2% rate requires several years of data. The $p$-value should therefore be read as evidence, not proof, and supplemented with the window-sensitivity analysis in section6.

---

## 4. Independence and conditional coverage

### 4.1 Christoffersen lag-1 independence test

Tests whether a breach on day $t$ predicts a breach on day $t+1$. Introduced by Christoffersen (1998).

#### 4.1.1 Intuition

A model that produces the right number of breaches can still violate the VaR assumption by bundling them in one week, because a correctly specified VaR should make each day's breach probability independent of what happened yesterday. If the probability of a breach today is materially higher after a breach yesterday, breaches are clustering on consecutive days and the iid Bernoulli assumption fails.

#### 4.1.2 Construction

From the breach indicator sequence, build a 2×2 transition count matrix:

|              | To 0 (no breach) | To 1 (breach) |
|--------------|:----------------:|:-------------:|
| **From 0**   | $n_{00}$         | $n_{01}$      |
| **From 1**   | $n_{10}$         | $n_{11}$      |

where $n_{ij}$ is the number of transitions from state $i$ to state $j$ (state 0 = no breach, state 1 = breach).

From these four counts, compute two conditional breach probabilities:

$$\hat{\pi}_{01} \;=\; \frac{n_{01}}{n_{00}+n_{01}} \;=\; P(\text{breach today} \mid \text{no breach yesterday})$$

$$\hat{\pi}_{11} \;=\; \frac{n_{11}}{n_{10}+n_{11}} \;=\; P(\text{breach today} \mid \text{breach yesterday})$$

and the unconditional rate, ignoring what happened yesterday:

$$\hat{\pi} \;=\; \frac{n_{01}+n_{11}}{n_{00}+n_{01}+n_{10}+n_{11}} \;=\; \frac{\text{total breaches}}{\text{total days}}$$

#### 4.1.3 Test statistic

The likelihood-ratio statistic compares two models:

- **Null hypothesis:** every day has the same breach probability regardless of history: $\hat{\pi}_{01} = \hat{\pi}_{11} = \hat{\pi}$.
- **Alternative hypothesis:** the breach probability depends on whether yesterday was a breach — typically $\hat{\pi}_{11} > \hat{\pi}_{01}$ when breaches cluster on consecutive days.

For each model, compute the likelihood of observing the actual sequence of transitions, then take twice the log-ratio:

$$\text{LR}_{\text{IND}} \;=\; 2\big[\,\ell(\hat{\pi}_{01},\hat{\pi}_{11}) \;-\; \ell(\hat{\pi})\,\big]$$

where the two log-likelihoods are:

$$\ell(\hat{\pi}_{01},\hat{\pi}_{11}) \;=\; n_{00}\ln(1-\hat{\pi}_{01}) + n_{01}\ln\hat{\pi}_{01} + n_{10}\ln(1-\hat{\pi}_{11}) + n_{11}\ln\hat{\pi}_{11}$$

$$\ell(\hat{\pi}) \;=\; (n_{00}+n_{10})\ln(1-\hat{\pi}) + (n_{01}+n_{11})\ln\hat{\pi}$$

Under the null, $\text{LR}_{\text{IND}} \sim \chi^2(1)$. The single degree of freedom comes from the dimensionality gap between the models (two parameters vs one). Reject at the 5% level if $\text{LR}_{\text{IND}} > 3.84$.

#### 4.1.4 What this test does and does not detect

The test detects clustering at lag 1 only. Breaches on consecutive days increase $\hat{\pi}_{11}$ and drive rejection. Breaches separated by more than one day — even if the gaps are systematically short — do not affect $n_{11}$ at all, and the test has no power against this pattern. Multi-week clustering, the pattern most often produced by historical simulation during a volatility regime shift, is invisible. See section7 for the outlook on the duration-based test that addresses this limitation.

### 4.2 Conditional coverage test

Combines the Kupiec frequency test (section 3) and the independence test (section 4.1) into a single joint statistic. Introduced by Christoffersen (1998) alongside the independence test.

#### 4.2.1 Intuition

A correctly specified VaR must satisfy two properties simultaneously: the right number of breaches (frequency) and independent breaches (timing). Kupiec checks the first; the independence test checks the second. The conditional coverage test asks the joint question: are the breaches both correctly sized *and* correctly spaced?

In practice, $\text{LR}_{\text{CC}}$ contains no information beyond what its two components provide separately, and diagnosis still requires inspecting the components. The joint test is documented here because it is referenced in regulatory and academic literature, because it provides a single summary $p$-value, and because it controls the joint type-I error when two hypotheses are tested simultaneously (running Kupiec and the independence test separately at 5% each gives a joint type-I error closer to 10%).

#### 4.2.2 Construction

The test exploits a convenient property of likelihood-ratio statistics: when two null hypotheses are independent, their LR statistics simply add, and the degrees of freedom add too. Kupiec tests $H_0: \hat{\pi} = p_0$ (one restriction on frequency). The independence test tests $H_0: \hat{\pi}_{01} = \hat{\pi}_{11}$ (one restriction on timing). These restrictions are independent, so:

$$\text{LR}_{\text{CC}} \;=\; \text{LR}_{\text{POF}} \;+\; \text{LR}_{\text{IND}} \;\sim\; \chi^2(2)$$

Reject at the 5% level if $\text{LR}_{\text{CC}} > 5.99$, equivalently $p$-value < 0.05.

#### 4.2.3 Diagnosing a rejection

When the joint test rejects, inspect the components:

| $\text{LR}_{\text{POF}}$ | $\text{LR}_{\text{IND}}$ | Interpretation |
| --- | --- | --- |
| Rejects | Does not reject | Frequency is wrong — too many or too few breaches |
| Does not reject | Rejects | Frequency is correct, but breaches cluster on consecutive days |
| Rejects | Rejects | Both properties fail |
| Does not reject | Does not reject | Joint test will not reject either |

---

## 5. Expected Shortfall backtesting

### 5.1 Intuition

The VaR tests in section 3 and section 4 address frequency and timing of breaches but are silent on severity. A model may produce the correct proportion of breaches while systematically underestimating how bad losses are when they occur. Under FRTB, 97.5% ES replaces 99% VaR as the primary internal model risk measure, and model evaluation must include an ES-specific check.

The notebook uses the bootstrap coverage-ratio diagnostic (section 5.2). The formal hypothesis-testing framework is Acerbi-Székely (2014), discussed as an outlook in section 7.

### 5.2 ES coverage ratio (diagnostic)

For each breach day, record the realized loss and the ES estimate produced by the model. The coverage ratio is the mean of the former divided by the mean of the latter:

$$\text{Coverage ratio} \;=\; \frac{\overline{L}_{\text{realized}}}{\overline{\text{ES}}_{\text{model}}}$$

- **Ratio ≈ 1.0:** model correctly sizes the average tail loss.
- **Ratio > 1.0:** model underestimates tail severity — under-reservation.
- **Ratio < 1.0:** model is over-conservative in the tail.

A 95% bootstrap confidence interval around the ratio is constructed by resampling the breach-day loss/ES pairs with replacement. The decision rule used in the notebook is: **reject** $H_0$ (correctly calibrated ES) if the entire bootstrap CI lies above 1.0.

### 5.3 Interpreting the diagnostic at small samples

At one year of backtest data, the number of breach days at 97.5% ES is small (roughly 6 expected; 2–3 at 99% VaR). Any ES test built on breach-day losses is therefore working with few observations, and the practical consequence matters: a binary reject/don't-reject verdict at small $N$ is uninformative, because the absence of rejection may reflect either correct calibration or insufficient power.

The coverage-ratio diagnostic is well-suited to this situation for one specific reason: **it reports a magnitude with a confidence interval, not just a $p$-value**. A reading "ES underestimates tail severity by 25%, 95% CI [10%, 47%]" has substantive information about the direction and size of the mis-calibration even when $N$ is too small for a formally sized test to reject. A reader of a null $p$-value at the same sample size has less to work with.

This is why the diagnostic is the appropriate choice for the current backtest horizon, not merely a concession to informality. Its limitation is the one already noted: the decision rule (CI strictly above 1.0) is heuristic and does not control type-I error at a specified level. For formal validation submissions, Acerbi-Székely is the expected framework; the outlook in section 7 covers the conditions under which it becomes worth adding.

---

## 6. Volatility models

The notebook implements two volatility models: flat historical simulation as the baseline, and EWMA volatility scaling as the principal enhancement.

### 6.1 Flat historical simulation

The VaR estimate at confidence $\alpha$ on day $t$ is the empirical $(1-\alpha)$-quantile of the portfolio returns over the preceding $W$ days, treating each observation as equally weighted. The ES estimate is the mean of returns below that quantile.

**Strengths:** non-parametric, free of distributional assumptions, simple to implement and explain.

**Weaknesses:** treats every day in the window as equally relevant, ignoring volatility clustering. Slow to adapt to regime shifts. Sensitive to window length.

### 6.2 EWMA volatility scaling

Exponentially Weighted Moving Average (EWMA) weights recent observations more heavily. The standard recursion, following RiskMetrics conventions:

$$\hat{\sigma}^2_t \;=\; \lambda \cdot \hat{\sigma}^2_{t-1} \;+\; (1-\lambda) \cdot r^2_{t-1}$$

RiskMetrics uses $\lambda = 0.94$ for daily data, corresponding to an effective half-life of about 11 trading days. A higher $\lambda$ (e.g. 0.97) produces smoother, slower-adapting estimates; a lower $\lambda$ reacts faster but is noisier.

In the notebook, EWMA is applied as a volatility-scaling overlay on historical simulation: historical returns are rescaled by the ratio of the current EWMA forecast to the EWMA volatility at the time each return was observed, and the empirical quantile of the rescaled set is taken as the VaR estimate. This preserves the non-parametric tail shape of historical simulation while making the estimate responsive to the current volatility regime.

### 6.3 Window-size sensitivity

The choice of window $W$ materially affects the VaR level and the breach count. A verdict that depends on a single window choice is weaker than one that is robust across a range of reasonable windows. The notebook runs the backtest at multiple window lengths (typically 20, 40, 60, 90, 120 days) and reports the Kupiec verdict at each. Disagreement across windows is itself informative and is reported alongside the headline result.

---

## 7. Outlook: tests for longer backtest horizons

Two tests with meaningful theoretical standing are documented here but not applied in the current notebook, because their power depends on sample sizes the current backtest does not support. Both become useful at roughly the same horizon — three to four years of daily data, giving enough tail observations to support formal inference.

### 7.1 Christoffersen-Pelletier duration test

The lag-1 independence test in section 4.1 detects clustering at consecutive days only. Christoffersen & Pelletier (2004) proposed a duration-based alternative that examines the full distribution of gaps between breaches, detecting clustering at any lag.

#### 7.1.1 Construction

The test works with the inter-breach durations $\{d_i\}$ rather than the breach indicator. Under the null hypothesis of iid Bernoulli($p_0$) breaches, these durations are geometrically distributed with mean $1/p_0$ and are memoryless. The test nests the geometric null inside a two-parameter Weibull alternative:

$$f(d;\,a,\,b) \;=\; \frac{a}{b}\left(\frac{d}{b}\right)^{a-1}\exp\!\left[-\left(\frac{d}{b}\right)^a\right]$$

When $a = 1$ the Weibull reduces to the exponential — the continuous-time equivalent of the geometric null. Shape parameter deviations encode the independence violation:

| Shape $\hat{a}$ | Hazard | Interpretation |
| :-: | --- | --- |
| $\hat{a} = 1$ | Constant | Memoryless — null holds |
| $\hat{a} < 1$ | Decreasing | Clustering in short bursts |
| $\hat{a} > 1$ | Increasing | Over-dispersed |

The test statistic compares the Weibull MLE against the restricted exponential:

$$\text{LR}_{\text{IND}}^{\text{CP}} \;=\; 2\big[\,\ell(\hat{a},\hat{b}) \;-\; \ell(1,\hat{b})\,\big] \;\sim\; \chi^2(1)$$

#### 7.1.2 Why it is not applied now

Fitting a two-parameter Weibull requires a reasonable number of inter-breach durations to produce stable estimates. A common rule of thumb is at least ten durations, equivalent to roughly four years of backtest data at 99% VaR. The current backtest does not yet support this.

### 7.2 Acerbi-Székely formal ES tests

Acerbi & Székely (2014) resolved a long-standing open question about whether ES could be formally backtested given its non-elicitability. They proposed three test statistics (Z₁, Z₂, Z₃), each constructed to have expected value zero under the null of correctly calibrated ES, with well-defined null distributions obtained by Monte Carlo simulation.

- **Z₁ (conditional):** uses realized losses on breach days only. Direct counterpart to the coverage ratio but with a proper null distribution and controlled type-I error.
- **Z₂ (unconditional):** uses all observations, weighting each by how far into the tail it falls. More data-efficient than Z₁.
- **Z₃ (quantile-based):** uses the rank of realized returns in the model's forecast distribution. Highest power in simulation studies and particularly useful for catching distributional mis-specification.

Significance is determined via Monte Carlo simulation under the null distribution assumed by the model. Acerbi-Székely is the industry-standard formal ES backtest and the reference framework for FRTB model validation.

#### 7.2.1 Why it is not applied now

Z₁ uses the same handful of breach-day observations as the coverage ratio — at one year of data, this is 2–3 observations at 99% VaR, 6 at 97.5% ES. Z₂ and Z₃ use more of the sample but their power is still ultimately limited by the number of tail observations. At the current horizon, the Z-tests would rarely reject unless the mis-calibration were very large, and a null $p$-value at small $N$ carries less information than the magnitude-plus-CI summary from the coverage-ratio bootstrap in section 5.2.

Acerbi-Székely becomes worth adding when any of the following hold:

1. The backtest horizon grows to three to four years, producing enough tail observations to support formal inference.
2. Formal validation (MRM, internal audit, regulatory) specifically requires it.
3. The ES model moves to a parametric form (e.g., Student-t innovations, GPD tail fit) where distributional mis-specification — which Z₃ in particular can detect — becomes the primary concern. At that point Z₃ provides information the coverage ratio cannot.

Until any of these applies, the diagnostic in section 5.2 remains the appropriate ES check.

---

## 8. Basel Traffic Light Framework

### 8.1 Purpose

The Basel Committee on Banking Supervision (1996 Market Risk Amendment, retained under Basel II/III) specifies a traffic-light classification mapping backtest results to regulatory capital treatment. It operationalises the Kupiec test into a zone-based framework with predefined capital consequences.

### 8.2 Zone definitions

For a 250 trading-day backtest at 99% VaR, the zones and capital multiplier add-ons are:

| Zone | Breaches (250d) | Multiplier add-on | Interpretation |
| --- | :-: | :-: | --- |
| Green | 0 – 4 | +0.00 | Model acceptable |
| Yellow | 5 | +0.40 | Under scrutiny — model may be flawed |
| Yellow | 6 | +0.50 | |
| Yellow | 7 | +0.65 | |
| Yellow | 8 | +0.75 | |
| Yellow | 9 | +0.85 | |
| Red | ≥ 10 | +1.00 | Automatic model review and recalibration |

### 8.3 Capital consequence

The Basel III minimum multiplier floor is 3.0. The zone add-on is applied on top, giving an effective multiplier in the range 3.0 (Green) to 4.0 (Red). The regulatory capital requirement is this multiplier applied to the ten-day 99% VaR. A Yellow-zone breach of +0.50 raises the multiplier from 3.0 to 3.5, increasing the market-risk capital requirement by about 17%.

### 8.4 Zone scaling for non-standard windows

The Basel zones are specified for a 250-day window. For internal analysis using shorter windows (e.g. 192 days), one of two approaches is used:

- **Scaling.** Compute breach counts matching the same binomial CDF levels used in the original calibration. Under Binomial(250, 0.01) the Green cut-off at 4 corresponds to CDF ≈ 89%; the Yellow cut-off at 9 corresponds to CDF ≈ 99.99%. Applied to Binomial(192, 0.01), these produce scaled thresholds. This is a pragmatic internal choice but is not a regulatory standard.
- **Reporting without scaling.** State that the backtest window is shorter than Basel-standard and that the 250-day classification cannot yet be computed. This is the more conservative approach for regulatory submissions.

Whichever approach is used, the scaling rule must be documented and applied consistently across reporting periods.

---

## 9. Conventions and References

### 9.1 Unit conventions

| Quantity | Unit | Example | Rationale |
| --- | --- | --- | --- |
| Portfolio returns, VaR, ES | % | −2.50% | Natural unit for return-based risk measures |
| Instrument P&L contributions | bps | −32.5 bps | Daily contributions are sub-1%; bps is the market standard for attribution |
| Annualized volatility | % | 16.1% | Standard quoting convention |
| Vol utilization (loss in σ units) | × (multiples) | 3.0× | Dimensionless z-score |
| Capital multipliers | × (multiples) | 3.62× | Applied to ten-day VaR |
| Test statistics | unitless | LR = 8.09 | Likelihood-ratio / χ² values |
| $p$-values and probabilities | decimal | 0.0045 | Four decimal places, no % sign |

**Conversion:** 1 bps = 0.01%. To relate an instrument contribution to the portfolio-level return, divide the bps figure by 100 (e.g. UBSG −32.5 bps = −0.325% contribution to that day's portfolio return).

### 9.2 Glossary

- **Breach (exception, violation):** a day on which the realized loss exceeds the VaR estimate.
- **Confidence level (α):** the probability of not exceeding VaR on any given day.
- **Conditional coverage:** correct unconditional frequency and correct conditional timing jointly.
- **Coverage ratio:** mean realized loss on breach days divided by mean ES estimate on the same days.
- **EWMA:** Exponentially Weighted Moving Average, a volatility estimator weighting recent returns more heavily.
- **FRTB:** Fundamental Review of the Trading Book; the Basel market risk framework replacing Basel II/III market-risk rules.
- **Independence:** the property that today's breach does not depend on prior breaches.
- **Kupiec POF:** Proportion of Failures test; tests unconditional coverage.
- **Likelihood ratio (LR):** 2 × log-likelihood difference between restricted and unrestricted models; χ² under the null.
- **Out-of-sample:** evaluation on data not used in model fitting.
- **Unconditional coverage:** correct breach frequency over the backtest horizon.

### 9.3 References

- Basel Committee on Banking Supervision (1996). *Supervisory framework for the use of "backtesting" in conjunction with the internal models approach to market risk capital requirements.*
- Basel Committee on Banking Supervision (2019). *Minimum capital requirements for market risk (FRTB).*
- Christoffersen, P. (1998). Evaluating interval forecasts. *International Economic Review* 39, 841–862.
- Christoffersen, P. & Pelletier, D. (2004). Backtesting Value-at-Risk: a duration-based approach. *Journal of Financial Econometrics* 2, 84–108.
- Kupiec, P. (1995). Techniques for verifying the accuracy of risk measurement models. *Journal of Derivatives* 3, 73–84.
- Morgan/Reuters (1996). *RiskMetrics Technical Document*, 4th edition.

### 9.4 Document control

| Version | Date       | Author           | Change          |
|---------|------------|------------------|-----------------|
| 1.0     | 2026-04-18 | Martin Diergardt | Initial version |
