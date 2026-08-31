# Airport CVaR Optimization: A Tail-Risk-Aware Framework

_A Real-Time Optimization System for Multi-Modal Airport Departures, Applying a Conditional Value-at-Risk (CVaR) Framework to Incheon International Airport Terminal 1._

---

## 1. Project Overview

This repository provides a complete, reproducible research and engineering stack for **tail-risk-aware gate assignment and passenger routing** at Incheon International Airport (ICN) Terminal 1. The system is designed to provide personalized, risk-minimized route recommendations to passengers, from their point of arrival at the airport (e.g., railway, bus, taxi, parking) to their departure gate.

The core of the project is an integrated optimization engine combining **Conditional Value-at-Risk (CVaR) routing**, **hysteresis-based recommendation stabilization**, and **passenger-level personalization** within a single 5-minute decision cycle. Component-level decomposition (see Section 12) shows that these three mechanisms contribute to system performance through distinct, non-interchangeable channels: personalization is the primary driver of the framework's nominal mean-time and CVaR increase (an intentional equity-oriented buffer allocation for vulnerable passengers), the joint interaction of hysteresis and personalization drives recommendation-switch reduction, and the CVaR objective's distinct contribution to tail-risk resilience is most evident under distributional stress (e.g., weather shocks) rather than under nominal operating conditions. The system is built around **four operationally distinct but mathematically unified research questions (RQ1–RQ4)**, and evaluated through a **comprehensive thirteen-stage experimental battery (E1–E13)** that isolates each methodological contribution and assesses robustness beyond nominal conditions.

### **Four Research Questions (RQ1–RQ4)**

*Where does tail risk originate in the airport departure system?*

Each RQ corresponds to a **distinct ingress modality**, representing a different uncertainty structure and control problem.

| RQ      | Passenger Entry Mode                  | Core Uncertainty                 | Scientific Question                                                                                |
| ------- | ------------------------------------- | --------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **RQ1** | **Inside terminal (security → gate)** | Endogenous queue spillovers      | Can CVaR-based routing reduce missed-flight risk when congestion is volatile but data is reliable? |
| **RQ2** | **Rail → terminal → gate**            | Upstream delay propagation       | Can rail delay uncertainty be optimally absorbed before it cascades into security & gate queues?   |
| **RQ3** | **Taxi / curbside → terminal**        | Weather-driven congestion        | Can METAR-driven probabilistic weather models prevent curbside-induced tail delays?                |
| **RQ4** | **Parking → terminal → gate**         | Search + walking + transfer risk | Can parking occupancy and walking-time uncertainty be optimized to avoid extreme delays?           |

Together, these RQs create a **multi-modal stress test** of tail-risk management: from **high-frequency, high-reliability queues (RQ1)** to **low-frequency, high-variance access risks (RQ4)**.

### **Experimental Battery (E1–E13)**

*Which components actually reduce tail risk — and why?*

The core experiments (E1–E10) form a **causal ladder**, moving from data quality → risk modeling → control → stability → personalization → full system integration → robustness and stress testing. A supplementary battery (E11–E13) provides diagnostic, sensitivity, and decision-support analyses that support the interpretation of these results.

| Exp     | What is being tested                | Policy contrast                       | What it evaluates                                                                                       |
| ------- | ------------------------------------ | -------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **E1**  | **Data fusion**                     | Baseline vs Hybrid-Mean               | Whether probabilistic data blending improves tail prediction                                             |
| **E2**  | **Risk objective**                  | Hybrid-Mean vs Hybrid-CVaR            | How the CVaR objective interacts with personalization to reshape mean-time, CVaR, and stability outcomes |
| **E3**  | **Operational feasibility**         | CVaR w/ vs w/o hard constraints       | Whether risk-aware optimization respects real airport limits                                             |
| **E4**  | **Stability control**               | γ = 0 vs γ = 1.5 (hysteresis)         | Whether recommendation volatility can be controlled without hurting performance                          |
| **E5**  | **Personalization**                 | Generic vs passenger-specific         | Whether individual heterogeneity reduces prediction error                                                |
| **E6**  | **System integration**              | Q1 only vs Q1–Q4 combined             | Whether full multi-modal optimization dominates siloed routing                                            |
| **E7**  | **Out-of-time validation**          | Early vs late temporal split          | Whether policy effects persist across time periods                                                        |
| **E8**  | **Gate-agnostic transfer**          | In-domain vs out-of-domain gates      | Whether framework generalizes to unseen terminal zones                                                    |
| **E9**  | **Weather stress test**             | Baseline vs 5mm rainfall perturbation | Whether risk-aware policies are more resilient to shocks — the primary evidentiary basis for the CVaR objective's distinct value |
| **E10** | **Equity analysis**                 | Vulnerable vs general passenger groups | Whether reliability is prioritized for vulnerable populations                                            |
| **E11** | **Positivity / propensity diagnostics** | Logged propensity distribution     | Whether the identifiability conditions for off-policy evaluation hold (min propensity > 0.026)           |
| **E12** | **Stability–efficiency–equity frontier** | Pareto-frontier across policies   | How operators can select a policy configuration for a given institutional risk tolerance                 |
| **E13** | **Hyperparameter sensitivity**      | ±25% parameter perturbation           | Whether policy outcomes are robust to moderate miscalibration of penalty weights                          |

### Key Features

- **Real-Time Data Ingestion**: Fetches live departure gate congestion data from the Incheon Airport Corporation's public API (B551177).
- **External Data Fusion**: Integrates METAR weather reports (from KMA) and official passenger forecasts to build a rich, contextual understanding of airport conditions.
- **Probabilistic Passenger Modeling**: Utilizes Bayesian imputation and personalized models to estimate walking speeds and check-in times based on passenger profiles (e.g., age, mobility, baggage).
- **Distributional Forecasting**: Employs an ensemble of predictive models (Markov Chain, Kalman Filter, Quantile Heuristics) to forecast the entire probability distribution of gate wait times, not just a single point estimate.
- **CVaR-Based Optimization**: The core optimization agent scores potential routes using a CVaR-inclusive objective function.
- **Hysteresis & Stability**: Incorporates a penalty for switching recommendations frequently; empirically, this stabilizing effect is realized jointly with personalization rather than as an independent, orthogonal mechanism (see Section 12).
- **Equity-Aware Personalization**: Individualized route scoring functions as a bias-correction and buffer-allocation mechanism for vulnerable passenger groups, and is the primary source of the framework's nominal mean-time and CVaR cost.
- **Causal Evaluation Framework**: Implements Doubly Robust (DR) estimators with snapshot-level bootstrap confidence intervals for unbiased off-policy evaluation within the offline replay environment.
- **Robustness Testing**: Evaluation through out-of-time, gate-agnostic transfer, and weather stress tests, assessing behavior beyond nominal operating conditions.
- **Offline Experimentation Framework**: Includes a robust offline replay and evaluation module to run simulated A/B tests (E1–E13) on historical data.
- **Advanced Analytics & Reporting**: Generates publication-grade statistical analyses, including Welch's t-tests, Cohen's d for effect size, Holm-Bonferroni correction for multiple comparisons, and exports a wide range of results and visualizations.

The entire codebase is designed to be deterministic and reproducible. Once the database is populated using the provided scripts, all experiments and analyses will yield identical results.

> **Note on scope**: All results in this repository are derived from an offline replay simulation using historical data snapshots and synthetic passenger journeys. They are not derived from live operational deployment or observed passenger behavior. See Section 11 for a description of the robustness tests conducted within this offline environment.

---

## 2. System Architecture

The system is designed with a modular, pipeline-oriented architecture:

```
[APIs: Congestion, METAR, Forecast]
             |
             v
[1. Ingestion Layer] -> (RealtimeCongestionService, ExternalDataIngestor)
     - Fetches and persists raw data to MySQL.
     - Handles API retries and fallbacks.
             |
             v
[2. Feature Engineering Layer] -> (T1FeatureBuilder)
     - Fuses data sources.
     - Computes features like load-to-capacity ratio, queue pressure, and risk scores.
     - Persists features to the Feature Store (MySQL).
             |
             v
[3. Prediction Layer] -> (Ensemble: Kalman, Markov, Heuristic)
     - Generates distributional forecasts for gate wait times.
     - Blends real-time observations with predictions based on data quality.
             |
             v
[4. Optimization Layer] -> (OptimizationAgent)
     - Models passenger-specific travel times (walking, check-in).
     - Scores all possible routes using the CVaR-inclusive objective function.
     - Applies penalties for gate closures, missed flights, and recommendation switching (hysteresis).
             |
             v
[5. Application Layer] -> (AirportOptimizationEngine, ExperimentRunner)
     - Exposes functionality via an interactive CLI (Q1-Q4).
     - Runs automated offline replay experiments (E1-E13) to evaluate policies.
             |
             v
[6. Analytics Layer] -> (OfflineReplayAnalyzer)
     - Loads experiment logs from the database.
     - Computes performance metrics (APT, CVaR, Miss Rate).
     - Performs statistical significance testing, component decomposition, and generates reports.
```

---

## 3. Repository Layout

```
airport-cvar-optimization/
├─ README.md
├─ LICENSE
├─ requirements.txt
├─ pyproject.toml
├─ .env.example
├─ config/
│ ├─ mysql_config_template.yml
│ └─ logging.yaml
├─ sql/
│ ├─ 00_create_schema.sql
│ └─ 01_alter_columns.sql
├─ src/
│ ├─ init.py
│ ├─ settings.py
│ ├─ db/
│ ├─ ingest/
│ ├─ models/
│ ├─ utils/
│ ├─ pipeline/
│ └─ analytics/
├─ scripts/
│ ├─ run_interactive.py
│ ├─ run_experiments.py
│ └─ export_reporting.py
├─ tests/
├─ notebooks/
│ ├─ 00_environment_check.ipynb
│ ├─ 01_run_migrations.ipynb
│ ├─ 02_realtime_pipeline.ipynb
│ ├─ 03_offline_replay_E1_E6.ipynb
│ ├─ 04_statistical_analysis.ipynb
│ └─ 05_appendix_figures.ipynb
├─ output/
└─ .gitignore
```

---

## 4. Prerequisites

| Component | Version / Notes |
|-----------|-----------------|
| Python    | 3.10+ |
| MySQL     | 8.x (or compatible, e.g., Aurora MySQL) |
| APIs      | Incheon Airport Corp (B551177) & KMA METAR service keys |
| OS        | Linux/macOS/WSL2 recommended. Windows is supported. |

---

## 5. Environment Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/airport-cvar-optimization.git
    cd airport-cvar-optimization
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate   # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    Copy the example file and edit it with your credentials. **Never commit the `.env` file.**
    ```bash
    cp .env.example .env
    nano .env
    ```
    You will need to provide your MySQL connection details and API service keys.

5.  **Set up the database:**
    Connect to your MySQL server and create the database.
    ```bash
    mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS icn_airport_analysis CHARACTER SET utf8mb4;"
    ```

6.  **Run database migrations:**
    This script will create and alter all necessary tables idempotently.
    ```bash
    python -m src.db.migrations
    ```
    You can also run this from the `01_run_migrations.ipynb` notebook to verify.

---

## 6. How to Run

The system can be operated in three main modes via the `scripts/` directory.

### Mode 1: Interactive CLI

Run a live, interactive session to get route recommendations for different scenarios (Q1-Q4).

```bash
python scripts/run_interactive.py
```

### Mode 2: Automated Experiments

Run the full offline replay simulation (E1-E13). This script will:
1.  Collect a stream of real-time data snapshots.
2.  Simulate thousands of passenger decisions under various policies.
3.  Log all evaluation data and summary metrics to the MySQL database.

```bash
# Run with default parameters (180 min duration, 5 min interval, etc.)
python scripts/run_experiments.py

# Run with custom parameters
python scripts/run_experiments.py --duration 120 --interval 5 --users 10 --epsilon 0.1
```

### Mode 3: Reporting and Analysis

After running an experiment, generate a full statistical report from the logged data.

```bash
# Replace <uuid> with the ID from the experiment run
python scripts/export_reporting.py --experiment-id <your-experiment-uuid>
```
This will produce an `output/` directory containing a comprehensive set of results.

---

## 7. Generated Outputs

Running the analysis script (`export_reporting.py` or `04_statistical_analysis.ipynb`) produces a rich set of outputs in the `output/` directory, including:

-   **Primary Report (`airport_experiment_results.xlsx`)**: An Excel workbook containing all key data tables on separate sheets.
-   **Core Metrics (CSV)**:
    -   `policy_summary.csv`: Overall performance metrics (APT, CVaR, Miss Rate, Switch Rate) for each policy.
    -   `Q4_metrics.csv`: Detailed metrics for the Q4 (Parking) scenario, used for primary policy comparisons.
    -   `e6_metrics.csv`: Performance of the main CVaR policy across all scenarios (Q1-Q4).
    -   `Q4_ci.csv`: Bootstrapped 95% confidence intervals for mean and CVaR metrics.
-   **Statistical Tests (CSV)**:
    -   `e1_e5_tests.csv`: Results of Welch's t-tests, Cohen's d, and Holm-Bonferroni corrected p-values for key policy comparisons (E1-E5).
-   **Component Decomposition**:
    -   `component_decomposition.csv`: Sequential decomposition of the Hybrid-Mean → Hybrid-CVaR transition into (i) CVaR objective + hard constraints + hysteresis, and (ii) personalization, for each of the four journey scenarios (Q1–Q4).
-   **Advanced & Causal Analysis**:
    -   `causal_results.csv` & `causal_forest.png`: Outputs from causal inference models estimating the heterogeneous treatment effects of the CVaR policy.
    -   `bayesian_contrasts.csv` & `bayesian_contrast.png`: Bayesian analysis comparing the posterior distributions of policy performance.
    -   `propensity_overlap.png`: Visualization of the propensity score distribution to check for common support between treatment and control groups.
-   **Cost-Benefit & Sensitivity Analysis**:
    -   `cost_benefit.png` & `cost_benefit_summary.csv`: Visualization and data for the cost-benefit analysis, translating time differences into a monetary value (a passenger-side time-cost proxy; see Section 12).
    -   `cba_sensitivity.csv`: Sensitivity of the cost-benefit results to the assumed monetary valuation factor (±20%).
-   **Performance Visualizations**:
    -   `Q4_boxplot.png`: Boxplots comparing the distribution of total journey times for each policy.
    -   `Q4_tail_metrics.png`: Bar chart comparing tail-risk metrics (Q90, CVaR) across policies.
    -   `pareto_frontier.png`: A scatter plot illustrating the trade-off between efficiency (mean time), risk (CVaR), and equity, showing the Pareto-optimal policies (E12).
    -   `Q4_hourly_trend.png`: Line plot showing how performance metrics change over the time of day.
-   **Publication-Ready Figures (`figures/`)**: A dedicated subdirectory containing curated figures for research papers or presentations.

---

## 8. Notebook Workflow

The `notebooks/` directory provides a step-by-step guide to verifying the environment, running the pipeline, and analyzing the results.

1.  `00_environment_check.ipynb`: Validate Python dependencies and database connectivity.
2.  `01_run_migrations.ipynb`: Execute and verify the database schema setup.
3.  `02_realtime_pipeline.ipynb`: Walk through a single cycle of the data ingestion and feature engineering pipeline.
4.  `03_offline_replay_E1_E6.ipynb`: Programmatically trigger the `ExperimentRunner` and log the resulting experiment ID.
5.  `04_statistical_analysis.ipynb`: Load data from an experiment and perform the full analytical pipeline, including the component decomposition analysis, replicating the `export_reporting.py` script in an interactive format.
6.  `05_appendix_figures.ipynb`: Generate advanced visualizations, such as Pareto frontiers and causal effect plots.

---

## 9. Testing

Run unit tests to ensure individual components are working correctly.

```bash
# Run all fast unit tests
pytest

# Run integration tests (requires a populated database)
pytest -m integration
```

---

## 10. Data Governance and Security

- **Secrets Management**: All sensitive information (database credentials, API keys) is managed exclusively through the `.env` file, which is git-ignored.
- **Data Persistence**: All ingested data is stored in a user-controlled MySQL database. No data is stored in the repository.
- **PII**: The system uses synthetic passenger profiles and does not handle any Personally Identifiable Information.
- **API Compliance**: Ingestion scripts include automated retry with exponential backoff to respect provider rate limits.
- **Causal Identifiability**: Propensity scores are logged for all recommendations, enabling off-policy evaluation via Doubly Robust estimators within the offline replay environment. The positivity assumption is empirically checked (min propensity > 0.026); see the caveats on causal scope in Section 11.

---

## 11. Robustness Evidence (Offline Simulation)

All results below are derived from the offline replay environment described in Section 1 and are conditional on the synthetic passenger generation protocol. They provide evidence of robustness within this simulation environment; live operational validation is a direction for future work, not a claim made by this repository.

### Temporal Robustness (E7)
- **CVaR drift < 0.1%** across early/late temporal splits
- **Stable treatment effects**: DR-ATE for Hybrid-CVaR vs. Hybrid-Mean on APT = -0.20 min [95% CI: -0.36, -0.03]
- Indicates that the observed policy behavior is relatively stable over time within the evaluated setting

### Spatial Transferability (E8)
- **Zero constraint violations** on out-of-domain gates (DG5-6)
- **KL divergence = 0.770** between in-domain and out-of-domain recommendation distributions, suggesting adaptive, context-sensitive gate allocation rather than rigid replication of in-domain patterns
- Provides evidence of portability to unseen terminal configurations within the evaluated setting

### Environmental Resilience (E9) — Primary Evidence for the CVaR Objective's Distinct Value
- Under a simulated **5mm rainfall perturbation**:
  - Hybrid-CVaR: CVaR₀.₉ relative deterioration = **9.3%** (absolute increase +4.53 min)
  - Hybrid-Mean: CVaR₀.₉ relative deterioration = **10.0%** (absolute increase +3.92 min)
- Hybrid-CVaR shows a smaller *relative* deterioration despite a larger *absolute* increase — consistent with the theoretical expectation that a coherent tail-risk measure binds most under distributional stress rather than under nominal conditions. This 0.7-percentage-point margin is modest and was evaluated under a single shock magnitude; see the manuscript's Discussion (§8.5) for this limitation.

### Equity Analysis (E10)
- **Equity Gap (vulnerable vs. general passengers)**: +7.83 min for Hybrid-CVaR, vs. +0.03 min for Hybrid-Mean — an intentional buffer allocation for vulnerable groups, not an unintended disparity
- Personalization-driven bias corrections: +4.17 to +7.58 min across the four journey types (effect sizes d > 1.1)
- A quasi-binomial logistic regression on miss probability confirms these segment-specific risk profiles are statistically significant

### Diagnostic and Sensitivity Battery (E11–E13)
- **E11 (positivity diagnostics)**: minimum observed propensity > 0.026 across all policies, with no evidence of weak overlap
- **E12 (stability–efficiency–equity frontier)**: a three-axis Pareto frontier supporting policy selection under different institutional risk tolerances
- **E13 (hyperparameter sensitivity)**: APT variance = 0.075 and CVaR variance = 0.284 under ±25% perturbation of the penalty weights, indicating limited sensitivity to moderate miscalibration

---

## 12. Key Performance Results

From 34,560 simulated passenger journeys across 36 historical snapshots.

### 12.1 Aggregate Policy Comparison

| Metric | Baseline | Hybrid-Mean | Hybrid-CVaR (Proposed) |
|--------|----------|-------------|------------------------|
| **APT (min)** | 37.18 | 37.15 | 43.51 |
| **CVaR₀.₉ (min)** | 48.95 | 47.17 | 62.39 |
| **Switch Rate (%)** | 19.4 | 20.3 | 20.9 (26.0% vs. an unconstrained CVaR-only variant, a 65.7% relative reduction) |
| **Constraint Violations** | — | — | **0%** (0/34,560); 6.83% under the unconstrained ablation variant |
| **Temporal Drift (E7)** | — | — | **< 0.1%** |
| **Out-of-Domain Violations (E8)** | — | — | **0 / 4,754** on DG5-6 |

Hybrid-CVaR shows **higher** nominal APT and CVaR₀.₉ than Hybrid-Mean, not lower. This is an intentional design outcome, not an error: see Section 12.2.

### 12.2 What Drives the Nominal APT and CVaR Increase?

A component-decomposition analysis — sequentially adding (i) the CVaR objective, hard constraints, and hysteresis, then (ii) personalization, to the Hybrid-Mean baseline — shows:

| Journey Scenario | Δ APT from CVaR obj. + constraints + hysteresis | Δ APT from Personalization | Personalization Share |
|---|---|---|---|
| Q1 (Check-in → Gate) | +0.15 min | +4.17 min | 96.5% |
| Q2 (Rail → Gate) | −0.03 min | +6.98 min | 100.4% |
| Q3 (Curbside → Gate) | −0.003 min | +5.10 min | 100.1% |
| Q4 (Parking → Gate) | +0.15 min | +7.57 min | 98.1% |

**96–101% of the nominal APT and CVaR₀.₉ increase from Hybrid-Mean to Hybrid-CVaR is attributable to passenger-level personalization** — an intentional equity-oriented buffer allocation for vulnerable passengers (Section 11, Equity Analysis) — **not to the CVaR objective itself**. The CVaR-NoPersonalization ablation variant confirms this directly: with personalization removed, APT and CVaR₀.₉ revert to levels statistically indistinguishable from Hybrid-Mean.

The CVaR objective's distinct contribution to tail-risk management is instead evidenced under distributional stress (Section 11, E9), where it shows smaller relative CVaR deterioration than Hybrid-Mean.

### 12.3 What Drives the Switch-Rate Reduction?

Nested ablation comparisons show that recommendation stability depends on the **joint** operation of hysteresis and personalization, not on either mechanism alone:

| Configuration transition | Switch Rate change | Interpretation |
|---|---|---|
| Hybrid-Mean → CVaR-NoPersonalization (CVaR obj. + hysteresis, no personalization) | 64.9% → 80.0% (**worse**) | Hysteresis alone, without personalization, does not stabilize recommendations |
| CVaR-NoPersonalization → Hybrid-CVaR (adds personalization) | 80.0% → 26.0% | Personalization is necessary for hysteresis's stabilizing effect to materialize |
| Hybrid-Mean → CVaR-NoHysteresis (personalization, no hysteresis) | 64.9% → 59.2% | Personalization alone yields limited stability improvement |
| CVaR-NoHysteresis → Hybrid-CVaR (adds hysteresis) | 59.2% → 26.0% | Hysteresis substantially improves stability once personalization is present |

A full factorial ablation (rather than the sequential single/paired-removal design used here) would be required to fully isolate higher-order interactions; this is noted as a limitation in the manuscript.

---

## 13. License

This project is licensed under the MIT License. See the `LICENSE` file for details.
