# Airport CVaR Optimization: Attributing the Effects of a Tail-Risk-Aware Departure Guidance Policy

_An offline replay framework for multimodal airport departures at Incheon International Airport (ICN) Terminal 1. It combines quality-weighted distributional prediction, a Conditional Value-at-Risk (CVaR) routing objective, hard constraints, a hysteresis switching penalty, and passenger-level personalization, and it attributes the effects of each component through ablation._

---

## 1. Project Overview

This repository provides a reproducible research and engineering stack for evaluating **tail-risk-aware passenger routing** at ICN Terminal 1. For each passenger, the system recommends a route from the point of arrival (inside the terminal, rail, curbside bus or taxi, or parking) to a departure gate. Throughout this repository, **"gate" denotes one of the 12 departure security checkpoints of Terminal 1**, not an aircraft boarding gate.

The routing engine integrates the following components within a single 5-minute decision cycle:

- quality-weighted distributional prediction,
- a CVaR objective (mean and 90th-percentile objectives are also supported),
- hard operating constraints,
- a hysteresis-based switching penalty, and
- passenger-level personalization.

Because the full policy differs from a mean-optimizing alternative in several components at once, no single component can be credited with the observed differences. The repository therefore **evaluates the bundle and then decomposes it through ablation variants**. The framing is operational: it asks which levers an airport operator controls (how much planning allowance each passenger segment receives, how reluctant guidance is to change, which part of the journey-time distribution to protect) and what each lever does to efficiency, stability, tail risk, and allocation.

### What the offline replay shows (summary)

All statements are conditional on the simulation protocol described in the scope note below.

- **Efficiency cost.** Moving from Hybrid-Mean to Hybrid-CVaR raises mean parking-to-gate journey time by 7.72 minutes. Along the decomposition path used, 7.57 minutes are attributable to personalization and 0.15 minutes to the CVaR objective, hard constraints, and hysteresis combined.
- **Stability.** Recommendation switching in the parking-to-gate scenario falls from 64.9% (Hybrid-Mean) to 26.0% (Hybrid-CVaR). The reduction appears only in the configuration that combines hysteresis and personalization; the nested design cannot separate their roles.
- **Allocation.** The Buffer Allocation Gap (BAG) between vulnerable and general passengers rises from 0.03 to 7.83 minutes. The gap arises from the personalization factors, which are generator inputs, so it is an implementation consistency check and not an empirical finding about real passengers.
- **CVaR objective.** The standalone contribution of the CVaR objective is **not established** under nominal conditions. A weather-shock test is consistent with a stress-time role but is confounded by personalization (see Section 11).
- **Constraints.** Hybrid-CVaR records zero constraint violations; removing the hard constraints yields 2,362 infeasible recommendations (6.83%).

### Journey types (Q1–Q4)

Four journey types are modeled. Q2–Q4 add one upstream stochastic stage ahead of the shared check-in-to-gate segment.

| Module | Passenger entry mode                  | Upstream uncertainty                 | Operational question                                                                 |
| ------ | ------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------ |
| **Q1** | **Inside terminal (check-in → gate)** | Queue spillovers at counters and gates | How should guidance route passengers when congestion is volatile but data are reliable? |
| **Q2** | **Rail → check-in → gate**            | Rail transfer and entry-queue delay  | How should rail-side delay uncertainty be absorbed before it reaches security and gate queues? |
| **Q3** | **Taxi / curbside → check-in → gate** | Weather-sensitive curbside queueing  | How should precipitation-driven curbside delay be reflected in guidance?             |
| **Q4** | **Parking → check-in → gate**         | Parking search plus walking and transfer | How should occupancy-dependent search time and walking-time uncertainty be handled?  |

### Research questions (RQ1–RQ3)

| RQ      | Question                                                                                                              |
| ------- | --------------------------------------------------------------------------------------------------------------------- |
| **RQ1** | How much of the efficiency cost of a bundled tail-risk-aware policy is attributable to each operator-controllable component? |
| **RQ2** | Which component or combination governs recommendation stability, and at what cost to efficiency and acceptance?       |
| **RQ3** | How does the policy allocate planning allowance across passenger segments, and can this be monitored with a single metric (the BAG)? |

### Experimental battery (E1–E13)

*Which components carry which effects, and how robust are the results?*

The ten core experiments (E1–E10) address the research questions and robustness. Three supplementary analyses (E11–E13) provide diagnostics, a policy-selection view, and sensitivity checks.

| Exp     | Focus                          | Policy contrast                                          | Research question | What it evaluates                                                                           |
| ------- | ------------------------------ | -------------------------------------------------------- | ----------------- | --------------------------------------------------------------------------------------------- |
| **E1**  | Data fusion                    | Baseline vs. Hybrid-Mean                                 | Context for RQ1   | Effect of quality-weighted blending on Q90 and switching (partly built into the simulator, see Section 11) |
| **E2**  | Bundled policy                 | Hybrid-Mean vs. Hybrid-CVaR, decomposed via CVaR-NoPersonalization | RQ1     | Attribution of the mean-time, CVaR, miss-rate, and switch-rate changes                       |
| **E3**  | Hard constraints               | Hybrid-CVaR vs. CVaR-NoConstraints                       | RQ1               | Violation rate with and without constraints                                                  |
| **E4**  | Hysteresis                     | γ = 0 vs. γ = 1.5                                        | RQ2               | Switch rate, mean time, CVaR, and acceptance                                                 |
| **E5**  | Personalization                | Generic vs. personalized profiles                        | RQ1, RQ3          | Average treatment effect on journey time                                                     |
| **E6**  | Journey complexity             | Q1 to Q4                                                 | Face validity     | Whether mean time and tail risk rise with the number of upstream stages                      |
| **E7**  | Chronological holdout          | First 18 vs. last 18 snapshots                           | Robustness        | CVaR drift over a short period                                                               |
| **E8**  | Unseen checkpoints             | In-domain (DG1–DG4) vs. out-of-domain (DG5–DG6)          | Robustness        | CVaR, violations, and KL divergence of recommendations                                       |
| **E9**  | Weather shock                  | 5 mm rainfall perturbation                               | RQ1 (exploratory) | Relative CVaR deterioration and miss rate under one shock magnitude                          |
| **E10** | Allocation                     | Vulnerable vs. general passengers                        | RQ3               | Buffer Allocation Gap                                                                        |
| **E11** | Positivity / propensity diagnostics | Logged propensity distribution                      | Diagnostic        | Overlap for off-policy evaluation (minimum propensity > 0.026)                               |
| **E12** | Stability–efficiency–equity frontier | Pareto view across policies                        | Supplementary     | A descriptive aid for policy selection; not part of the core attribution                     |
| **E13** | Hyperparameter sensitivity     | ±25% parameter perturbation                              | Diagnostic        | Robustness to moderate miscalibration of calibrated parameters                               |

### Key Features

- **Real-Time Data Ingestion**: Fetches live departure-gate congestion data from the Incheon Airport Corporation public API (B551177).
- **External Data Fusion**: Integrates METAR weather reports (KMA) and official passenger forecasts, with a source-level quality score and a tiered fallback hierarchy for degraded data.
- **Probabilistic Passenger Modeling**: Uses profile-based multiplicative factors (walking and check-in time) and Bayesian imputation for incomplete profiles.
- **Distributional Forecasting**: Combines an ensemble of predictive models (quantile heuristic, Markov–Kalman, Bayesian personalization) by an equal-weight average of predictive quantiles, then blends them with real-time observations according to data quality.
- **CVaR-Based Optimization**: Scores candidate routes with Monte Carlo scenarios (N = 200 per route) and a composite score that adds closure, delay, switching, and risk terms to the chosen objective.
- **Hysteresis**: Penalizes changing the recommendation between consecutive cycles. In the replay, its stabilizing effect was observed only jointly with personalization (Section 12.3).
- **Personalization and the BAG**: Passenger-level factors allocate planning allowance across segments. The BAG, the difference in mean journey time between vulnerable and general passengers, makes this allocation observable. It is a monitoring metric and does not enter the routing score.
- **Off-Policy Evaluation Machinery**: Implements inverse propensity scoring and doubly robust (DR) estimators with snapshot-level bootstrap intervals. In this simulator the DR and naive estimates coincide (Section 10), so the machinery serves as a consistency check for future live deployment.
- **Robustness Tests**: Chronological holdout, unseen-checkpoint transfer, a weather shock, and parameter-perturbation sensitivity.
- **Offline Experimentation Framework**: Runs offline replay experiments (E1–E13) on historical snapshots with identical synthetic passengers across policies.
- **Analytics and Reporting**: Welch's t-tests, Cohen's d, Cliff's delta, Holm–Bonferroni correction across the core experiments, and exports of tables and figures.

The codebase is deterministic: with the same database snapshots and the fixed random seed (42), experiments and analyses yield identical results.

> **Note on scope**: All results in this repository derive from an **offline replay** of 36 consecutive five-minute snapshots of real operational data (a 3-hour window) combined with **synthetic passenger journeys**. They are not derived from live deployment or observed passenger behavior. The simulator is *model-in-the-loop* (journey outcomes are sampled from the same distributions used for optimization), passenger compliance follows an assumed ε-greedy rule (ε = 0.2), and recommendations do not feed back into queue states. Personalization factors are generator inputs. See Section 11 for what is and is not validated. **This repository is a research tool and is not intended for operational use.**

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

Every decision, its inputs, and its quality annotations are stored under a single `snapshot_id`, so any decision can be reproduced exactly by offline replay.

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
    This script creates and alters all necessary tables idempotently.
    ```bash
    python -m src.db.migrations
    ```
    You can also run this from the `01_run_migrations.ipynb` notebook to verify.

The schema has eight tables in three functional domains: **operational** (`congestion_data`, `congestion_features_t1`), **predictive** (`passenger_forecast_raw`, `passenger_forecast_t1`, `metar_raw`), and **experimental** (`experiment_runs`, `experiment_metrics`, `policy_evaluation_log`). The `snapshot_id` is the temporal join key, and `experiment_id` and `policy_version` provide experimental traceability. Data follow a bronze, silver, and gold layering: raw API responses, parsed and validated data with quality annotations, and feature-engineered datasets for the prediction ensemble.

---

## 6. How to Run

The system can be operated in three main modes via the `scripts/` directory.

### Mode 1: Interactive CLI

Run an interactive session to get route recommendations for the journey types Q1–Q4.

```bash
python scripts/run_interactive.py
```

### Mode 2: Automated Experiments

Run the offline replay experiments (E1–E13). This script will:
1.  Collect a stream of real-time data snapshots.
2.  Simulate passenger decisions under the policy configurations, using identical synthetic passengers for every policy.
3.  Log all evaluation data and summary metrics to the MySQL database.

```bash
# Run with default parameters (180 min duration, 5 min interval)
python scripts/run_experiments.py

# Run with custom parameters
python scripts/run_experiments.py --duration 120 --interval 5 --users 10 --epsilon 0.1
```

A 180-minute duration at a 5-minute interval yields 36 snapshots. The reported study used **960 synthetic passengers per snapshot (34,560 journeys)** and an assumed compliance rate of **ε = 0.2**; set `--users` and `--epsilon` accordingly to match the study design. The custom-parameter example above is for quick smoke tests only.

### Mode 3: Reporting and Analysis

After running an experiment, generate a full statistical report from the logged data.

```bash
# Replace <uuid> with the ID from the experiment run
python scripts/export_reporting.py --experiment-id <your-experiment-uuid>
```
This will produce an `output/` directory containing the results described below.

---

## 7. Generated Outputs

Running the analysis script (`export_reporting.py` or `04_statistical_analysis.ipynb`) produces the following in the `output/` directory:

-   **Primary Report (`airport_experiment_results.xlsx`)**: An Excel workbook containing the key data tables on separate sheets.
-   **Core Metrics (CSV)**:
    -   `policy_summary.csv`: Overall (pooled) performance metrics (APT, CVaR, miss rate, switch rate) for each policy.
    -   `Q4_metrics.csv`: Detailed metrics for the Q4 (parking) scenario, used for the primary policy comparisons.
    -   `e6_metrics.csv`: Performance of the main CVaR policy across the journey types Q1–Q4.
    -   `Q4_ci.csv`: Snapshot-level bootstrap 95% confidence intervals for mean and CVaR metrics.
-   **Statistical Tests (CSV)**:
    -   `e1_e5_tests.csv`: Welch's t-tests, Cohen's d, and Holm–Bonferroni-corrected p-values for key policy comparisons (E1–E5).
-   **Component Decomposition**:
    -   `component_decomposition.csv`: Sequential decomposition of the Hybrid-Mean → Hybrid-CVaR transition into (i) the CVaR objective, hard constraints, and hysteresis, and (ii) personalization, for each of the four journey types. The decomposition is path-specific; shares along the alternative ordering are not computed.
-   **Supplementary Causal and Bayesian Analyses (exploratory)**:
    -   `causal_results.csv` & `causal_forest.png`: Heterogeneous treatment-effect estimates for the CVaR policy.
    -   `bayesian_contrasts.csv` & `bayesian_contrast.png`: Posterior contrasts of policy performance.
    -   `propensity_overlap.png`: Propensity-score distribution for the common-support check (E11).
-   **Cost-Benefit and Sensitivity Analysis**:
    -   `cost_benefit.png` & `cost_benefit_summary.csv`: A passenger-side time-cost proxy that converts realized journey time into a monetary value. It excludes airport, airline, and ground-handling costs.
    -   `cba_sensitivity.csv`: Sensitivity of the cost ordering to the valuation factor (±20%).
-   **Performance Visualizations**:
    -   `Q4_boxplot.png`: Distribution of total journey times by policy.
    -   `Q4_tail_metrics.png`: Tail-risk metrics (Q90, CVaR) by policy.
    -   `pareto_frontier.png`: Descriptive trade-off view across efficiency, risk, and equity (E12, supplementary).
    -   `Q4_hourly_trend.png`: Metrics over the time of day.
-   **Publication-Ready Figures (`figures/`)**: A subdirectory containing curated figures.

**Naming note.** The metric called the *Buffer Allocation Gap (BAG)* in this README may appear as `equity_gap` or "Equity Gap" in output files and database fields from earlier versions.

---

## 8. Notebook Workflow

The `notebooks/` directory provides a step-by-step guide to verifying the environment, running the pipeline, and analyzing the results.

1.  `00_environment_check.ipynb`: Validate Python dependencies and database connectivity.
2.  `01_run_migrations.ipynb`: Execute and verify the database schema setup.
3.  `02_realtime_pipeline.ipynb`: Walk through a single cycle of data ingestion and feature engineering.
4.  `03_offline_replay_E1_E6.ipynb`: Programmatically trigger the `ExperimentRunner` and log the resulting experiment ID.
5.  `04_statistical_analysis.ipynb`: Load data from an experiment and perform the full analytical pipeline, including the component decomposition, replicating `export_reporting.py` interactively.
6.  `05_appendix_figures.ipynb`: Generate additional visualizations, such as the Pareto view and causal-effect plots.

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
- **Data Persistence**: All ingested data are stored in a user-controlled MySQL database. No data are stored in the repository. Use of the public IIAC and KMA data follows the providers' terms of service; retention should be limited to 90 days.
- **PII**: The system uses synthetic passenger profiles and does not handle any personally identifiable information.
- **API Compliance**: Ingestion scripts include automated retry with exponential backoff to respect provider rate limits.
- **Causal Identifiability**: Propensity scores are logged for all recommendations. Three assumptions underlie the off-policy evaluation. *Snapshot ignorability* holds conditional on the logged state. *Positivity* is enforced by the ε-greedy rule and checked empirically (minimum propensity > 0.026, no overlap cell below 2%). *SUTVA* holds by construction because passenger outcomes are sampled independently and recommendations do not feed back into queues. Consequently, **the DR and naive estimates coincide to two decimals** in this simulator: propensities are near uniform, importance weights approach unity, and DR reduces to the naive estimator. The DR pipeline is therefore a consistency check, not an independent test of the policies. In live deployment, where passengers self-select, the correction would matter.

---

## 11. Robustness Evidence and Validation Status (Offline Simulation)

All results below derive from the offline replay environment described in Section 1 and are conditional on the synthetic passenger generation protocol. They provide evidence of internal consistency within this simulation; live or shadow-mode validation is a necessary next step and is not claimed here.

### 11.1 What the replay verifies and what it does not validate

| Item                              | Status                    | Evidence and limitation                                                                                  |
| --------------------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Exact reproducibility             | Verified                  | `snapshot_id` lineage and fixed seed (42)                                                                 |
| Monte Carlo sample size           | Verified                  | CVaR estimates stabilize (coefficient of variation < 2%) at N ≥ 150; N = 200 runs in under 0.8 s per cycle |
| Hard-constraint handling          | Verified by contrast      | Zero violations under Hybrid-CVaR vs. 2,362 (6.83%) under CVaR-NoConstraints; zero holds by construction  |
| Positivity and estimator agreement | Checked                  | Minimum propensity > 0.026; DR and naive estimates agree to two decimals                                  |
| Parameter sensitivity             | Checked                   | ±25% on calibrated parameters (E13); ±10% on constraint thresholds                                        |
| Input snapshots                   | Real data                 | IIAC and KMA streams; only 36 snapshots (3 hours)                                                         |
| Parking search model              | Consistent with literature | 5.6 and 10.1 min at occupancies 0.60 and 0.90; not compared with measured search times                   |
| Journey-time distributions        | **Not validated**         | Not compared with observed passenger journeys                                                             |
| Passenger compliance              | **Assumed**               | ε-greedy with ε = 0.2; no sensitivity analysis to the compliance rule has been performed                  |
| Personalization factors           | Generator inputs          | Effects are conditional on the generator's profile model                                                  |
| Queue feedback                    | **Absent**                | Herding and congestion feedback are not simulated; switch-rate results measure recommendation stability, not its effect on queues |
| Scalability                       | Partly tested             | 12 Terminal 1 checkpoints under 0.8 s per cycle; larger networks untested                                 |

### 11.2 Robustness results

**Temporal robustness (E7).** CVaR₀.₉ drifted by less than 0.1% between the first 18 and last 18 snapshots (90 minutes each). This is a stability check over a limited period, not a test of seasonal or long-run drift.

**Spatial transfer (E8).** Calibrated on DG1–DG4 and tested on DG5–DG6, the framework achieved CVaR₀.₉ = 60.7 minutes with zero constraint violations. The KL divergence between in-domain and out-of-domain recommendation distributions is 0.770, which shows that allocations change in the new context; whether the change is appropriate was not assessed.

**Weather shock (E9, exploratory).** Under a simulated 5 mm rainfall perturbation:

| Policy       | Unperturbed CVaR₀.₉ (approx.) | Absolute increase | Relative deterioration | Miss rate under shock |
| ------------ | ----------------------------- | ----------------- | ---------------------- | --------------------- |
| Hybrid-Mean  | ≈ 39.2 min                    | +3.92 min         | 10.0%                  | 0.00%                 |
| Hybrid-CVaR  | ≈ 48.7 min                    | +4.53 min         | 9.3%                   | 0.90%                 |

Unperturbed levels are back-calculated from the reported increases and relative deteriorations, and are computed on a separate shock-replay set, so they are not comparable with the pooled values in Section 12. Hybrid-CVaR shows a slightly smaller *relative* but larger *absolute* increase and a higher miss rate. The smaller relative deterioration **cannot be attributed to the CVaR objective**: personalization raises Hybrid-CVaR's unperturbed level and mechanically lowers the relative measure, and the test included neither CVaR-NoPersonalization nor more than one shock magnitude. E9 is therefore treated as consistent with, but not proof of, a stress-time role for tail-risk objectives.

**Allocation (E10).** The BAG is +7.83 min for Hybrid-CVaR, vs. +0.03 min for Hybrid-Mean and +0.04 min for CVaR-Generic. The gap is the intended consequence of the personalization factors and does not arise from the routing objective, because no equity penalty enters the score. Its magnitude mirrors the generator's cohort corrections (+1.8 to +15.2 min by cohort) and should be read as an implementation consistency check, not as evidence about real passenger populations. Personalization effects on journey time range from +4.17 to +7.58 minutes across the four journey types (all p < 0.001; Cohen's d between 1.12 and 1.31).

**Diagnostics (E11–E13).**
- **E11**: minimum observed propensity > 0.026 across policies, with no overlap cell below 2%.
- **E12**: a descriptive three-axis (efficiency, risk, equity) view across policies for policy selection; it is not part of the core attribution.
- **E13**: APT variance = 0.075 and CVaR variance = 0.284 under ±25% perturbation of the calibrated parameters.

---

## 12. Key Performance Results

From 34,560 simulated passenger journeys across 36 historical snapshots. Intervals are 95% snapshot-level bootstrap intervals unless stated otherwise.

### 12.1 Aggregate (pooled) policy comparison

| Policy                  | APT (min)               | CVaR₀.₉ (min) | Acceptance (%) | Miss rate (%) |
| ----------------------- | ----------------------- | ------------- | -------------- | ------------- |
| Baseline                | 37.18 [37.01, 37.35]    | 48.95         | 80.6           | 0.00          |
| Hybrid-Mean             | 37.15 [36.99, 37.31]    | 47.17         | 79.7           | 0.00          |
| **Hybrid-CVaR**         | 43.51 [43.26, 43.76]    | 62.39         | 79.1           | 0.40          |
| CVaR-NoHysteresis       | 43.50 [43.25, 43.75]    | 62.93         | 80.8           | 0.52          |
| CVaR-NoPersonalization  | 37.23 [37.07, 37.39]    | 47.17         | 80.5           | 0.00          |

Hybrid-CVaR shows **higher** pooled APT (+6.36 min, 17.1%) and CVaR₀.₉ (+15.22 min) than Hybrid-Mean, not lower. CVaR-NoPersonalization returns to Hybrid-Mean levels, so the increase comes from personalization and not from the CVaR objective, the hard constraints, or hysteresis. **The framework does not lower nominal tail risk relative to Hybrid-Mean.**

Hard constraints: 0 violations in 34,560 journeys under Hybrid-CVaR (guaranteed by construction through a large closure penalty) vs. 6.83% infeasible recommendations (2,362) under CVaR-NoConstraints.

Pooled switch rates by policy are written to `policy_summary.csv`; the switch-rate comparisons reported below use the Q4 (parking-to-gate) scenario.

### 12.2 What drives the nominal APT increase?

A component decomposition sequentially adds (i) the CVaR objective, hard constraints, and hysteresis, then (ii) personalization, to Hybrid-Mean (`component_decomposition.csv`):

| Journey type             | Δ APT, CVaR obj. + constraints + hysteresis | Δ APT, personalization | Personalization share |
| ------------------------ | -------------------------------------------- | ---------------------- | --------------------- |
| Q1 (Check-in → Gate)     | +0.15 min                                    | +4.17 min              | 96.5%                 |
| Q2 (Rail → Gate)         | −0.03 min                                    | +6.98 min              | 100.4%                |
| Q3 (Curbside → Gate)     | −0.003 min                                   | +5.10 min              | 100.1%                |
| Q4 (Parking → Gate)      | +0.15 min                                    | +7.57 min              | 98.1%                 |

In Q4, 7.57 of the 7.72 minutes (Hybrid-Mean 41.89 → Hybrid-CVaR 49.61; 95% CI for the total change 6.51 to 8.89; Cohen's d = 1.17) are attributable to personalization along this path. The miss rate rises from 0.00% to 0.82% in Q4, and this increase is likewise tied to personalization. The attribution follows one path (Hybrid-Mean → CVaR-NoPersonalization → Hybrid-CVaR); because interactions may be present, "attributable" should be read as path-specific.

The personalization effect follows from the generator's profile model, which assigns longer walking and check-in times to non-generic profiles. It quantifies the **planning allowance the framework allocates**, not an efficiency gain and not evidence that real generic predictions are biased.

### 12.3 What is associated with the switch-rate reduction?

Q4 switch rates by configuration:

| Configuration                                              | CVaR obj. | Personalization | Hysteresis | Switch rate (Q4) |
| ---------------------------------------------------------- | --------- | --------------- | ---------- | ---------------- |
| Hybrid-Mean                                                | No        | No              | No         | 64.9%            |
| CVaR-NoPersonalization                                     | Yes       | No              | Yes        | 80.0%            |
| CVaR-NoHysteresis                                          | Yes       | Yes             | No         | 59.1%            |
| **Hybrid-CVaR**                                            | Yes       | Yes             | Yes        | **26.0%**        |

The reduction to 26.0% is **observed only in the configuration that combines hysteresis and personalization**. Hysteresis did not reduce switching when personalization was absent (80.0%, an unexpected result that is not explained here), and personalization without hysteresis lowered it only modestly. Because these configurations also differ in objective, and no configuration removes hysteresis while personalization is absent, the nested design supports only the statement that the *combination is associated with* the reduction, not that either component is necessary. One untested explanation is that personalization changes the spread of route scores so that a fixed switching penalty becomes comparable to score differences between routes. A full factorial ablation (objective × personalization × hysteresis) is required to quantify interactions.

Effect of hysteresis within the personalized CVaR policy (Q4): switch rate 59.1% → 26.0% (56.0% relative reduction), with no significant change in mean time (ATE = +0.05 min, 95% CI −0.20 to 0.25, p = 0.740) or CVaR₀.₉ (66.58 → 66.04 min, p = 0.312). The pooled acceptance rate falls from 80.8% to 79.1% (−1.7 pp; nominal p = 0.042, a borderline result treated as indicative, not established).

Effect of data fusion in Q4 (E1, Baseline → Hybrid-Mean): switch rate 75.7% → 64.9% and Q90 −1.88 min (both p < 0.001), with a non-significant mean-time change (−0.21 min, p = 0.097). Because outcomes are sampled from the blended distributions, this gain is partly built into the model-in-the-loop simulator.

### 12.4 What is and is not established

| Question                                        | Established in the replay                                                                  | Not established                                                                              |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Where does the nominal mean-time cost come from? | Personalization (96–101% of the increase, path-specific)                                   | Whether the allowances match real passenger needs                                            |
| What stabilizes recommendations?                | Hysteresis combined with personalization (59.1% → 26.0%)                                   | The separate roles of the two; effects on queues and passenger trust                         |
| Does the CVaR objective help?                   | No standalone effect under nominal conditions                                              | Any benefit under stress or predictive misspecification (the design cannot isolate it)       |
| Are operating limits respected?                 | Zero violations (by construction); 6.83% infeasible without constraints                    | Behavior under real rule changes                                                             |
| How is allowance allocated across segments?     | BAG 0.03 → 7.83 min, traceable to personalization                                         | An appropriate target level; real-population equity                                           |

**Suggested extensions** that this repository does not yet implement: a full factorial design crossing objective, personalization, and hysteresis; stress tests that include CVaR-NoPersonalization across several shock magnitudes and confidence levels; a decision-divergence rate (the share of decisions in which the mean and CVaR objectives select different routes); sensitivity to the compliance rule; comparison of simulated journey-time distributions with observed journeys; and shadow-mode operation in which recommendations are logged but not shown.

---

## 13. License

This project is licensed under the MIT License. See the `LICENSE` file for details.
