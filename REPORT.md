## Risk Analysis Report: Multi-Asset Fund

**Analyst:** Filippo Biagini

**Date:** 25.04.2026

**Time spent:** ~35 hours incl. time to design the pipeline, Docker architecture and risk dashboard to make it more production-oriented. Docker was kind of new to me, but I focused on understanding how to containerize the app end-to-end, e.g., Dockerfile and docker-compose setup. 

**What I prioritized:** To get the design and orchestration of the app correctly, validating the risk metrics calculations and backtesting results. Through the interpretation of the assessment's results, I highlighted in the sections below potential extensions of the current framework.

**Use of AI:** I used AI tools such as ChatGPT to boost productivity by refining the code structure, debugging the code and checking better ways to improve code execution. I inspected and validated all the lines of code, incl. manual validation for certain metrics. I used AI more extensively to accelerate the UI development with Streamlit as the framework is more having to deal with layout, components and quick iteration.


## 1. Executive Summary
This project implements a containerized risk analytics pipeline for a CHF 500M multi-asset fund with exposures to Swiss and European equities  as well as CHF and EUR govvies and corporate bonds, hence with sensitivity to equity market movements, interest rate shifts and credit spread movements.

The pipeline framework delivers end-to-end market risk analytics, covering data ingestion/loading, data validation, controlled preprocessing steps of market data, return generation, estimation of core risk measures (Value-at-Risk (VaR), Expected Shortfall(ES), Component VaR and EWMA VaR), model validation via backtesting, scenario-based stress testing, and production of risk reports. A risk analytics dashboard helps to visualize and complement the report.

The main findings are:

	•The portfolio exhibits moderate daily volatility, with a historical 99% VaR of ~2.02%, consistent with a diversified equity–bond allocation. However, tail risk is materially higher, as reflected by historical ES (99%) of ~2.39% and stress losses exceeding -5% (> CHF 25m).

	•Historical, parametric, and EWMA risk measures are directionally consistent, but show meaningful dispersion:
	    •Parametric VaR > Historical VaR (95%) suggests the normal assumption is slightly conservative in the current regime.
	    •EWMA VaR < Historical VaR reflects low recent volatility and highlights pro-cyclicality.
	    •At the tail level, Historical ES >> Parametric ES, confirming fat-tailed behavior not captured by normal assumptions.
	    •The rolling EWMA VaR backtest (99%) shows 4 breaches vs ~1.92 expected, indicating a mild underestimation of tail risk.
        •The Kupiec test does not reject the model, confirming statistical acceptability; however, the visual evidence shows breach clustering, hence showing a reactive and pro-cyclicality behavior, typical of volatility-based risk models.
    
    •Stress testing reveals materially higher downside risk than model-based metrics, with:
	    •Global Equity Crash: ~-5.1% (-25.45m CHF)
	    •SNB rate shock: ~-4.9% (-24.55m CHF)
    This confirms that:
	•	Equity exposure is the dominant driver of tail risk.
	•	Interest rate risk is a relevant secondary driver
	•	Diversification benefits from bonds are present but limited under stress

    In addition, the Component VaR highlights concentration risk on equities.

Key take-aways:

From a risk monitoring perspective, the model requires improvements to reduce pro-cyclicality and a strong focus on ES models to capture tail risk.

From a backtesting perspective, the approach is to expand to the performance of the Christoffersen test as breach clustering was noted and to a prallel backtesting of all the models.

From a portfolio perspective, reducing equity exposure and increasing bond exposure, adding uncorrelated asset classes such as alternatives or using derivatives to create convex hedges, for instance with OTM index puts.

In this report I describe the core implementation as well as some of the sections include a paragraph titled “Extensions to the Current Framework” outlining potential enhancements to scale the risk engine toward a production-grade environment. 

## 2. Portfolio Overview and Risk Profile

The CHF 500 million multi-asset strategy portfolio is diversified across equities and fixed income instruments (i.e., a bond-equity portfolio). The allocation is based on five sub-asset classes with more details on the instruments described below.

## 2.1 Portfolio Composition
The allocation in equity is concentrated in large-cap, liquid names across Switzerland and Europe, while the allocation in fixed income combines sovereign exposure with investment-grade corporate bonds.
		
## 2.2 Key Risk Drivers
The portfolio’s risk profile is driven by a combination of equity market risk, interest rate risk, credit spread risk and FX risk. This is based on the asset classes included in the portfolio. It is key to understand the stress testing framework and the contribution of each asset class (or sub-asset class) on risk metrics such as VaR and ES.

In general, in a full multi-asset portfolio when the asset class composition is expanded to alternatives, then risks such as liquidity risk and valuation risk (e.g., marked-to-model) also arise.

## 3. Data Framework and Quality Controls

## 3.1 Data Sources and Structure
The following data sources are provided and used:

**Reference data (DuckDB database): this includes static metadata, portfolio holdings and fund-level details
**Market data (Parquet files): this includes time series data and scenario details.

## 3.2 Data Validation and Integrity Checks
Before starting with the data preprocessing step, validation and data integrity checks are performed to make sure that there is data consistency for the next step of risk calculations, for instance verification of the number of columns in the dataset, dates that are coming as time indices, flagging of duplicates and so on.

## 3.3 Data Cleaning Methodology
A data cleaning process was implemented to address common problems in the dataset which might lead to material impacts on the calculation of risk measures. 
In order to avoid this, I implemented the following logics:

**Duplicate handling: multiple observations with the same pair – date and instrument id being remediated.

**Missing prices: Forward-fill (ffill) followed by backward-fill (bfill) within each instrument series so that the time series no longer have gaps.

**Outlier detection in time series: I decided to set up a threshold of +/- 30% daily return with an in-depth analysis of the price time series when needed.

**Visual inspection: analysis of price time series and return distribution so that no extreme spikes due to data quality issues are observed.

### Extensions to the current framework

As always, the data cleaning approach above has been defined by taking certain assumption and limitations into consideration, for instance:

**Missing prices approach might not be appropriate if the price gap is created due to market stress.

**Outlier detection threshold can be set up differently for equity and bonds so as to better capture outliers.

**Other important elements related to the extension of the portfolio to illiquid assets have not been taken into account / modelled such as bid-ask spread, proxy definition, etc ...

## 4.Return Construction and Aggregation

## 4.1 Price Transformation and Return definition

After the data cleaning step, price data is transformed from long format into a matrix suitable for time series analysis and portfolio aggregation.
In order to achieve the computation of returns and the portfolio aggregation, the wide format structure is used.

Simple returns are calculated instead of the log returns as certain optimal properties are exploited such as linearity in portfolio aggregation and direct interpretability.

## 4.2 Portfolio Aggregation Methodology
Portfolio weights are derived from the latest snapshot of the positions_history table.
 
Portfolio returns are then calculated.
 
## 4.3 Validation of Return Series
To ensure the integrity of the constructed return series, several validation checks are performed.

** Structural validation
** Numerical checks
** Manual calculation to ensure consistency.
** Visual inspection of return series

### Extensions to the current framework
The current return construction approach considers static weights and simple return. 
In a more production-ready setup, the following improvements can be implemented:

**Time-varying weights: this aspect reflects the portfolio rebalancing component.
**Factor return decomposition, hence the portfolio return is defined as the multiplication between exposure to factors and factor returns.

## 5. Risk Measurement Framework

## 5.1 Overview of Risk Metrics

The risk measurement framework is designed to quantify potential portfolio losses under normal and stressed market conditions. 

The analysis focuses on three core metrics:

**Value-at-Risk (VaR), incl. EWMA VaR
**Expected Shortfall (ES)
**Component VaR (risk attribution)

These metrics are computed using both historical and parametric approaches to provide complementary perspectives on portfolio risk.

## 5.2 Historical VaR and Expected Shortfall
Historical VaR is computed using the empirical distribution of portfolio returns without imposing distributional assumptions.
 
Expected Shortfall (ES) is defined as the average loss conditional on exceeding the VaR threshold. 
 
## 5.3 Parametric VaR and Expected Shortfall
Parametric VaR assumes that portfolio returns follow a normal distribution characterized by mean and standard deviation.
  
## 5.4 Component VaR and Risk Attribution
Component VaR decomposes total portfolio risk into contributions from individual positions or sub-asset classes using a covariance-based approach.
 
## 5.5 Results

The following results were obtained:

** Historical VaR (95%): 0.95%

** Parametric VaR (95%): 1.05%

** Historical ES (99%): 2.39%
 
** Parametric ES (99%): 1.69%

** Component VaR (95%) - Component VaR is a 95% parametric VaR decomposition

   SWISS_EQUITY: 0.6756%
   EUR_EQUITY: 0.3356%
   CHF_CORP: 0.0343%
   EUR_GOVT: -0.0071%
   CHF_GOVT: -0.0105%

** EWMA VaR (95%): 0.73%

** EWMA VaR (99%): 1.03%

At the 95% level, the empirical distribution appears relatively benign, leading to a slightly lower historical VaR compared to the parametric estimate.

However, the significantly higher historical Expected Shortfall confirms thepresence of fat tails and more severe losses beyond the VaR threshold.

Component VaR is predominantly driven by equity exposure with some negative contributions from the bond part. Credit spreads seem not to be a primary driver.

EWMA VaR is well calibrated but slightly underestimates extreme tail risk and reacts rather than anticipates shocks.

## Extensions to the current framework
The current framework can be extended to enhance robustness and realism, for instance market regimes, factor mapping decomposition, etc..

**Non-normal distributions
**Factor-based VaR

## 6. Backtesting and Model Validation

## 6.1 Backtesting Framework and Assumptions
The backtesting framework is designed to assess the accuracy and calibration of the Value-at-Risk (VaR) model by comparing predicted risk levels with realized portfolio returns.

## Methodology
A rolling historical backtest is implemented with the following characteristics:

**Estimation window: 60 trading days
**Confidence level: 99%
**Frequency: daily

**Out-of-sample testing:
o	VaR is estimated using the previous 60 observations
o	Compared against the next day realized return

At each time step ( t ), the VaR estimate is computed using historical returns over the window ( [t-60, t-1] ), and evaluated against the realized return at time ( t ).

I performed the backtesting on the EWMA VaR (99%), hence I expect losses to exceed VaR about 1% of the time. With 192 observations, the expected number of breaches is close to 2 (~1.92).

## Breach Analysis

The backtesting results yield actual breaches equal to 4. This means that is above the expected breaches, hence the model is slighlty underestimating the risk in the tails. However, the Kupiec test does not reject the model at the 95% statistical confidence level (i.e., p-value=0.1878 > 0.05).

From this point and looking at the graph in the dashboard, it is clear that the EWMA VaR is reactive, not predictive with the increase of the VaR occurring after the shock, experiencing a sort of pro-cyclical behavior. The latter is typical for volatility-based risk models.

## Extensions to the current framework

It can be noted visually from the graph that there is a breach clustering.

I would have liked to extend the backtest with Christoffersen’s independence test to detect clustering that Kupiec test alone is not able to capture.

## 7. Stress Testing and Scenario Analysis

The analysis of the stress testing results highlights that the equity exposure drives downside to the portfolio in those scenarios 
where equity and interest rate risk arise. This also explains the sensitivity of the portfolio to these scenarios. 
On the European Sovereign Debt stress scenario, the portfolio gets some diversification benefits (i.e., component VaR was already highlighting that the credit spread risk is not a primary driver of the portfolio) which lead to smaller losses.

The worst case scenario is the Global Equity Crash confirmed also by the fact that 98% of the EWMA VaR is driven by equities.

If we look all together meaning VaR and ES models, the stress losses are substantially larger, confirming the presence of extreme tail risk beyond model-based estimates. This means that for further improvements a greater focus on ES models needs to be placed (see Executive Summary section).

## 8. Production Architecture and Implementation

## 8.1 System Design and Modularity

As per the assignment, the risk analytics solution is designed as a layered system, where each component has a defined task. 
This separation of tasks enhances maintainability, testability and scalability.

The core modules are Python files structured as follows:

•	data_loader
    ** Handles data ingestion from DuckDB and Parquet data sources
    ** Implements data cleaning and validation logic

•	risk_metrics
    **Computes VaR, Expected Shortfall, EWMA VaR, Component VaR, etc..
    **All statistical risk methodologies

•	backtest
    **Implements rolling VaR backtesting 
    **Performs model validation using the Kupiec test

•	stress
    **Applies predefined stress scenarios
    **Computes scenario-based portfolio P&L

•	reporting
    **Generates structured outputs (JSON, CSV, PNG, TXT)
    **Acts as the interface between analytics and stakeholders

•	run_analysis.py
    **Serves as the orchestration layer
    **Coordinates execution of the full pipeline

•	streamlit_app.py
    ** Risk Dashboard designed in Streamlit

## 8.2 Data and Process Flow
The pipeline follows a sequential, reproducible process from raw data to risk outputs.

Data Flow Overview
Raw Data (DuckDB + Parquet)
        ↓
Data loading & Data cleaning
        ↓
Price transformation & Return calculation
        ↓
Risk Metric Computation (VaR, ES, Component VaR, EWMA VaR)
        ↓
Backtesting (Model Validation for EMWA VaR model)
        ↓
Stress Testing (Scenario Analysis)
        ↓
Reporting (JSON / CSV / PNG / TXT)
        ↓
Risk Dashboard in Streamlit


## 8.3 Containerization and Deployment
The solution is containerized using Docker and orchestrated via docker-compose, reflecting a standard deployment approach for production risk systems.

## Dockerfile Design

The Dockerfile contains:

**A lightweight Python base image
**Installation of required dependencies (requirements.txt)
**Copying of source code and data into the container
**Execution of the pipeline via: python run_analysis.py

The docker-compose.yml orchestrates the execution environment:

**Builds the Docker image.
**Mounts the output/ directory as a volume.
**Ensures that results generated inside the container are accessible externally.

The full pipeline is executed via:

docker compose up --build

This command:

**Builds the container
**Runs the full analysis pipeline
**Writes outputs to the host system
**Dashboard becomes available


## Appendix – IT Architecture diagram

## System Architecture Overview

Data Sources
(DuckDB + Parquet)
        │
        ▼
Data Loading & Cleaning
(data_loader.py)
        │
        ▼
Returns & Aggregation
(prices → returns → portfolio - returns.py)
        │
        ▼
Risk Engine
(risk_metrics.py)
        │
   ┌────┴────┐
   ▼         ▼
Backtest   Stress
(backtest.py) (stress.py)
   └────┬────┘
        ▼
Reporting
(reporting.py → JSON / CSV / PNG / TXT)
        │
        ▼
Output (/output/)
        │
        ▼
 Risk Dashboard in Streamlit
 (streamlit_app.py)
        │
        ▼
Docker Execution
(docker-compose)
