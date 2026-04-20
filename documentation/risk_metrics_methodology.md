# Risk Metrics — Methodology

This document covers the risk metrics implemented in `risk_metrics.py` and demonstrated in the accompanying notebook. It explains what each measure computes, the formulas used, and how to interpret the results.

---

## 1. Portfolio Return Distribution

All risk metrics in this project operate on the portfolio's daily return series, constructed as the weighted sum of individual instrument returns:

$$r_{p,t} = \sum_i w_i \cdot r_{i,t}$$

Before computing any risk metric, it is useful to examine the shape of this distribution — specifically, how fat the tails are relative to a normal distribution. The QQ-plot in the notebook quantifies this: if the observed tail quantiles lie below the normal line, the distribution has heavier tails than a Gaussian, which means historical VaR will exceed parametric VaR at high confidence levels.

---

## 2. Value at Risk (VaR)

VaR answers: *"What is the maximum loss I expect to see on all but the worst α% of days?"*

At **99% confidence** the VaR is the loss threshold that is exceeded on only 1% of trading days — roughly 2–3 times per year for a 250-day series.

### 2.1 Historical simulation

**Formula:**

```text
VaR = −percentile(returns, 1%)    # for 99% confidence
```

**Steps:**

1. Sort all daily returns from worst to best.
2. Find the return at the 1st percentile (the bottom 1% of days).
3. Negate it — losses are positive by convention.

**Strength:** captures the true shape of the distribution including fat tails and skewness.

**Weakness:** entirely backward-looking; a calm period underestimates future risk.

### 2.2 Parametric (variance-covariance)

**Formula:**
$$\text{VaR} = -\mu + \sigma \cdot z_{\alpha}$$

where $\mu$ is the sample mean, $\sigma$ the sample standard deviation, and $z_{\alpha} = \Phi^{-1}(\text{confidence})$ is the normal quantile (`norm.ppf(0.99) ≈ 2.326` for 99%).

**Strength:** fast, analytically tractable, scales to large portfolios.

**Weakness:** the normality assumption underestimates tail risk when returns are fat-tailed or skewed.

### 2.3 Historical vs parametric comparison

When tails are fatter than normal, historical VaR exceeds parametric VaR at high confidence levels. The divergence grows with the confidence level because the parametric formula underestimates the probability mass in the extreme tail. At 90% confidence the two methods typically agree; the gap becomes significant at 99%.

---

## 3. Conditional VaR (CVaR) — Expected Shortfall

VaR tells us *where* the tail begins but says nothing about *how bad* losses in the tail are. Two portfolios can have identical VaR yet very different worst-case losses.

**CVaR** (also called Expected Shortfall, ES) answers: *"Given that we are already in the worst 1% of days, what is the average loss?"*

$$\text{CVaR} = -\mathbb{E}[R \mid R < -\text{VaR}]$$

CVaR ≥ VaR always, and the gap reflects the severity of tail risk beyond the VaR threshold.

### 3.1 Parametric CVaR formula

For a normal distribution the tail expectation has a closed form:

$$\text{CVaR} = -\mu + \sigma \cdot \frac{\phi(z_{\alpha})}{\alpha}$$

where $\phi$ is the standard normal PDF and $\alpha = 1 - \text{confidence}$.

The ratio $\phi(z_{\alpha})/\alpha$ is the **inverse Mills ratio** — it measures how much probability density lies in the tail relative to its probability mass. For $\alpha = 0.01$: $\phi(-2.326)/0.01 \approx 2.67$, so parametric CVaR is roughly 2.67 standard deviations from the mean.

---

## 4. Component VaR — Euler Decomposition

Portfolio VaR is a single number for the whole portfolio. Component VaR answers: *"How much does each position contribute to total VaR?"*

### 4.1 Degree-1 homogeneity and Euler's theorem

**Euler decomposition** exploits the fact that parametric VaR is a **degree-1 homogeneous function** of the weights. A function $f$ is homogeneous of degree 1 if scaling all inputs by $\lambda > 0$ scales the output by the same factor:

$$f(\lambda\,\mathbf{w}) = \lambda\,f(\mathbf{w})$$

Parametric VaR satisfies this because:
$$\text{VaR}(\lambda\mathbf{w}) = z_\alpha\sqrt{(\lambda\mathbf{w})^\top\Sigma(\lambda\mathbf{w})} = \lambda\,z_\alpha\sqrt{\mathbf{w}^\top\Sigma\mathbf{w}} = \lambda\,\text{VaR}(\mathbf{w})$$

By **Euler's theorem** for degree-1 homogeneous functions:

$$\text{VaR}_{\text{total}} = \sum_i w_i \cdot \frac{\partial \text{VaR}}{\partial w_i}$$

The partial derivative $\partial\text{VaR}/\partial w_i$ is the **marginal VaR** — the rate at which total VaR increases as position $i$ grows.

> Parametric VaR is **subadditive**: combining two portfolios reduces or at best preserves total VaR. This is the mathematical expression of **diversification benefit**.

### 4.2 Formula

$$\text{Component VaR}_i = w_i \cdot \frac{(\Sigma\, \mathbf{w})_i}{\sigma_p} \cdot z_{\alpha}$$

where $\Sigma$ is the covariance matrix, $\mathbf{w}$ the weight vector, and $\sigma_p = \sqrt{\mathbf{w}^\top \Sigma\, \mathbf{w}}$ the portfolio volatility.

**Key property:** component VaRs sum exactly to total VaR — unlike stand-alone VaRs which ignore diversification. Positions with a negative component VaR are portfolio diversifiers: their returns tend to be high when the portfolio loses.

---

## 5. Conventions

| Quantity | Unit | Example |
| --- | --- | --- |
| Portfolio returns, VaR, CVaR | % | −2.50% |
| Annualized volatility | % | 16.1% |
| Component VaR | return units (%) | +0.14% |
| $p$-values and probabilities | decimal | 0.0045 |

---

## 6. References

- Hull, J. C. (2018). *Options, Futures, and Other Derivatives*, 10th ed. Chapter 22.
- Morgan/Reuters (1996). *RiskMetrics Technical Document*, 4th edition.
- Roncalli, T. (2020). *Handbook on Financial Risk Management*. Chapter 4.

---

## 7. Document control

| Version   | Date         | Author           | Tooling     | Change          |
| --------- | ------------ | ---------------- | ----------- | --------------- |
| 1.0       | 2026-04-19   | Martin Diergardt | Claude Code | Initial version |
