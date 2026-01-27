# Airport CVaR Optimization: A Tail-Risk-Aware Framework

_A Real-Time Optimization System for Multi-Modal Airport Departures, Applying a Conditional Value-at-Risk (CVaR) Framework to Incheon International Airport Terminal 1._

---

## 1. Project Overview

This repository provides a complete, reproducible research and engineering stack for **tail-risk-aware gate assignment and passenger routing** at Incheon International Airport (ICN) Terminal 1. The system is designed to provide personalized, risk-minimized route recommendations to passengers, from their point of arrival at the airport (e.g., railway, bus, taxi, parking) to their departure gate.

The core of the project is an optimization engine that minimizes the **Conditional Value-at-Risk (CVaR)** of the total passenger journey time. Unlike traditional approaches that optimize for the average (mean) time, this framework focuses on mitigating the risk of experiencing excessively long delays (i.e., the "tail risk" of the travel time distribution).

### Key Features

- **Real-Time Data Ingestion**: Fetches live departure gate congestion data from the Incheon Airport Corporation's public API (B551177).
- **External Data Fusion**: Integrates METAR weather reports (from KMA) and official passenger forecasts to build a rich, contextual understanding of airport conditions.
- **Probabilistic Passenger Modeling**: Utilizes Bayesian imputation and personalized models to estimate walking speeds and check-in times based on passenger profiles (e.g., age, mobility, baggage).
- **Distributional Forecasting**: Employs an ensemble of predictive models (Markov Chain, Kalman Filter, Quantile Heuristics) to forecast the entire probability distribution of gate wait times, not just a single point estimate.
- **CVaR-Based Optimization**: The core optimization agent scores potential routes (e.g., drop-off point -> check-in counter -> security gate) by minimizing the CVaR of the total journey time distribution.
- **Hysteresis & Stability**: Incorporates a penalty for switching recommendations frequently, ensuring a more stable and less confusing user experience.
- **Offline Experimentation Framework**: Includes a robust offline replay and evaluation module to run simulated A/B tests (E1–E6) on historical data, comparing different policy configurations.
- **Advanced Analytics & Reporting**: Generates publication-grade statistical analyses, including Welch's t-tests, Cohen's d for effect size, Holm-Bonferroni correction for multiple comparisons, and exports a wide range of results and visualizations.

The entire codebase is designed to be deterministic and reproducible. Once the database is populated using the provided scripts, all experiments and analyses will yield identical results.

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
     - Scores all possible routes using the CVaR objective function.
     - Applies penalties for gate closures, missed flights, and recommendation switching (hysteresis).
             |
             v
[5. Application Layer] -> (AirportOptimizationEngine, ExperimentRunner)
     - Exposes functionality via an interactive CLI (Q1-Q4).
     - Runs automated offline replay experiments (E1-E6) to evaluate policies.
             |
             v
[6. Analytics Layer] -> (OfflineReplayAnalyzer)
     - Loads experiment logs from the database.
     - Computes performance metrics (APT, CVaR, Miss Rate).
     - Performs statistical significance testing and generates reports.
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

Run the full offline replay simulation (E1-E6). This script will:
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
-   **Advanced & Causal Analysis**:
    -   `causal_results.csv` & `causal_forest.png`: Outputs from causal inference models estimating the heterogeneous treatment effects of the CVaR policy.
    -   `bayesian_contrasts.csv` & `bayesian_contrast.png`: Bayesian analysis comparing the posterior distributions of policy performance.
    -   `propensity_overlap.png`: Visualization of the propensity score distribution to check for common support between treatment and control groups.
-   **Cost-Benefit & Sensitivity Analysis**:
    -   `cost_benefit.png` & `cost_benefit_summary.csv`: Visualization and data for the cost-benefit analysis, translating time savings into monetary value.
    -   `cba_sensitivity.csv`: Sensitivity analysis of the cost-benefit results under different assumptions.
-   **Performance Visualizations**:
    -   `Q4_boxplot.png`: Boxplots comparing the distribution of total journey times for each policy.
    -   `Q4_tail_metrics.png`: Bar chart comparing tail-risk metrics (Q90, CVaR) across policies.
    -   `pareto_frontier.png`: A scatter plot illustrating the trade-off between efficiency (mean time) and risk (CVaR), showing the Pareto optimal policies.
    -   `Q4_hourly_trend.png`: Line plot showing how performance metrics change over the time of day.
-   **Publication-Ready Figures (`figures/`)**: A dedicated subdirectory containing curated figures for research papers or presentations.

---

## 8. Notebook Workflow

The `notebooks/` directory provides a step-by-step guide to verifying the environment, running the pipeline, and analyzing the results.

1.  `00_environment_check.ipynb`: Validate Python dependencies and database connectivity.
2.  `01_run_migrations.ipynb`: Execute and verify the database schema setup.
3.  `02_realtime_pipeline.ipynb`: Walk through a single cycle of the data ingestion and feature engineering pipeline.
4.  `03_offline_replay_E1_E6.ipynb`: Programmatically trigger the `ExperimentRunner` and log the resulting experiment ID.
5.  `04_statistical_analysis.ipynb`: Load data from an experiment and perform the full analytical pipeline, replicating the `export_reporting.py` script in an interactive format.
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

---

## 11. Citation & License

Please cite the accompanying research paper if you use this code or framework in your work.

This project is licensed under the MIT License. See the `LICENSE` file for details.
