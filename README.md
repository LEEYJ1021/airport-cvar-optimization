# Who Gets the Buffer? Allocation and Stability in Airport Departure Guidance

_Replication code for an offline-replay study of departure guidance at Incheon International Airport (ICN) Terminal 1. The repository decomposes a bundled, tail-risk-aware guidance policy into operator-controllable levers (planning allowance, recommendation stability, tail-risk protection, hard operating limits) and introduces the **Buffer Allocation Gap (BAG)**, a monitoring indicator for vertical equity._

> **Research tool, not an operational system.** All results come from an offline replay of real operational snapshots combined with **synthetic passengers**. Passenger behavior, compliance and personalization effects are simulator-defined.

---

## 1. Project Overview

### 1.1 The planning question

Airport operators that issue departure guidance implicitly make two service-standard decisions, usually without stating or monitoring them:

1. **How much planning allowance (time buffer) does each passenger segment receive?**
2. **How often may a recommendation change?**

Both are distributional, public-sector decisions. This repository treats them as explicit operator levers and asks what each costs, and who bears it. The routing engine is the **instrument for comparing levers**, not a new optimization algorithm.

### 1.2 Four operator levers

| Lever | What the operator decides | Parameter in this study | Outcome dimension |
| ----- | ------------------------- | ----------------------- | ----------------- |
| Planning allowance (personalization) | How much buffer each segment receives | Profile factors on walking and check-in times | Allocation, mean time |
| Switching penalty (hysteresis) | How reluctant guidance is to change | γ = 1.5 score-minutes | Stability |
| Risk objective | Which part of the journey-time distribution to protect | CVaR at level 0.9, N = 200 scenarios per route | Tail risk |
| Hard operating constraints | Which limits are non-negotiable | Operating hours, capacities, deadlines, accessible routes | Feasibility |

Data-quality weighting and uncertainty inflation operate inside the engine; data fusion is varied only in E1.

### 1.3 Research questions

| RQ | Question | Gap addressed |
| -- | -------- | ------------- |
| **RQ1** | How much of the recommended-time cost of a bundled guidance policy is attributable to each operator-controllable lever? | A tail-risk-aware policy differs from a mean-optimizing one in several components at once, so no single component can be credited. |
| **RQ2** | Which lever or combination governs recommendation stability, and at what cost to efficiency and tail risk? | Instability is usually smoothed ad hoc, not through hysteresis. |
| **RQ3** | How does the policy allocate planning allowance across passenger segments, and can this be monitored with a single indicator? | Allocation through personalization is rarely observable to the operator. |

### 1.4 Journey types (Q1–Q4)

"Gate" denotes one of the **12 departure security checkpoints** of Terminal 1, not an aircraft boarding gate. Q2–Q4 add one upstream stochastic stage ahead of the shared check-in-to-gate segment.

| Module | Entry mode | Upstream uncertainty |
| ------ | ---------- | -------------------- |
| **Q1** | Check-in → gate | None (single-stage) |
| **Q2** | Rail → check-in → gate | Rail transfer and entry-queue delay |
| **Q3** | Curbside (bus or taxi) → check-in → gate | Weather-sensitive curbside queueing |
| **Q4** | Parking → check-in → gate | Occupancy-dependent parking search (2 + 10ρ², giving 5.6 and 10.1 min at occupancy 0.60 and 0.90) |

### 1.5 The Buffer Allocation Gap (BAG)

$$
\mathrm{BAG} = \mathbb{E}[T \mid \text{vulnerable}] - \mathbb{E}[T \mid \text{general}]
$$

- **Vulnerable passengers** meet at least one criterion: age ≥ 65; mobility score ≤ 2 on a 5-point scale (walking speed below 1.0 m/s); travel with one or more children under 12; or unaccompanied-minor status. All others, including heavy-baggage travellers, are *general*.
- The BAG is an **outcome indicator only**. It does not enter the routing score and no equity penalty is applied.
- **Remark 1 (BAG and cohort allowances).** If the non-personalization components change expected journey time by about the same amount for both groups, then BAG ≈ Δ₀ + ā_V − ā_G, where Δ₀ is the BAG without personalization and ā_V, ā_G are the cohort-weighted mean allowances. The BAG is therefore set by the **cohort allowances and the cohort mix, not by the routing objective**.
- The BAG is **not a quantity to minimize or maximize**. A zero gap under heterogeneous needs means vulnerable passengers receive generic plans; a large gap is the intended consequence when needs differ. It should be read against a **need-based reference** (the gap implied by measured segment differences in walking and processing times). A one-sided cap would cut the allowance whenever true need exceeds it, so a two-sided corridor around the reference is preferable (proposed, not tested).

### 1.6 Main findings (conditional on the replay)

| Question | Finding | Section / table in the manuscript |
| -------- | ------- | --------------------------------- |
| **RQ1**: where does the recommended-time cost come from? | Q4: Hybrid-Mean → Hybrid-CVaR adds **7.72 min** (18.4%) to mean time; **7.57 min** is attributable to personalization and **0.15 min** to the CVaR objective, constraints, switching penalty and risk inflation combined. Across journey types, personalization accounts for 96.5–100.4% of the APT increase, and the other components add less than 0.35 min to either APT or CVaR₀.₉. | §5.2, Table 5 |
| **RQ2**: what governs stability? | Q4 switch rate falls from 59.1% (CVaR-NoHysteresis) to **26.0%** (Hybrid-CVaR) with no significant change in mean time (+0.05 min, p = 0.740) or CVaR₀.₉ (p = 0.312). The effect is identified only **within the personalized policy**; without personalization the rate was 80.0% and the nested design cannot separate the two components. | §5.3, Table 6 |
| **RQ3**: how is allowance allocated? | Q4 **BAG = 7.83 min**, versus 0.03 (Hybrid-Mean) and 0.04 (CVaR-NoPersonalization). Cohort allowances range from +1.8 to +15.2 min. Heavy-baggage travellers receive +6.7 min yet are counted as general. | §5.4, Fig. 5 |
| Hard constraints | 0 violations under Hybrid-CVaR (by construction) versus **2,362 infeasible recommendations (6.83%)** without constraints. | §5.5 |
| Standalone CVaR objective | **Not established.** The bundle without personalization leaves pooled CVaR₀.₉ unchanged at the reported precision. | §5.1 |

**Price of the allocation decision.** The 7.57 min is the allowance itself, expressed in the unit passengers see. It is a single-point analogue of the price of fairness; a frontier would require the allowance sweep listed in [Section 14](#14-limitations-and-research-agenda).

> **Reading the numbers.** The personalization effect follows from the generator's profile model. It quantifies the buffer the framework allocates; it is neither evidence that generic predictions are biased nor an efficiency gain. The BAG magnitude mirrors the generator's cohort allowances and tests the simulator, not real populations.

---

## 2. System Architecture

### 2.1 From levers to outcomes

```
Operator levers                 5-minute routing engine                Monitored outcomes
-----------------               ------------------------               -------------------
Planning allowance   ─┐         1. Quality-weighted                    Efficiency  : APT
Switching penalty γ  ─┤──────►     distributional prediction  ───────► Tail risk   : CVaR0.9, miss rate
Risk objective       ─┤         2. Monte Carlo scenarios (N = 200)     Stability   : switch rate
Hard constraints     ─┘         3. Composite score → one recommendation Allocation : BAG
```

Every decision, its inputs and its quality annotations are stored under a single `snapshot_id`, so any decision can be reproduced exactly by offline replay.

### 2.2 Pipeline layers

```
[APIs: Congestion, METAR, Forecast]
             |
             v
[1. Ingestion Layer] -> (RealtimeCongestionService, ExternalDataIngestor)
     - Fetches and persists raw data to MySQL; handles retries and fallbacks.
             |
             v
[2. Feature Engineering Layer] -> (T1FeatureBuilder)
     - Fuses sources; computes load-to-capacity ratio, queue-pressure index,
       composite congestion risk score R; persists to the feature store.
             |
             v
[3. Prediction Layer] -> (Ensemble: Kalman, Markov, Heuristic)
     - Distributional forecasts of gate wait times, blended with real-time
       observations by a quality-dependent logistic weight.
             |
             v
[4. Optimization Layer] -> (OptimizationAgent)
     - Passenger-specific walking and check-in times (personalization).
     - Scores every candidate route with the composite score below.
             |
             v
[5. Application Layer] -> (AirportOptimizationEngine, ExperimentRunner)
     - Interactive CLI (Q1-Q4) and automated offline replay experiments.
             |
             v
[6. Analytics Layer] -> (OfflineReplayAnalyzer)
     - Metrics, statistical tests, component decomposition, reporting.
```

### 2.3 Routing objective and score

For each candidate route *j*, N = 200 Monte Carlo scenarios are drawn per cycle and total journey times T_j are built by summing all stochastic and deterministic components for the same draw. Three objectives are supported: expected time, the 90th percentile, and CVaR₀.₉ (the average of the worst 10% of simulated outcomes, by sample average approximation):

$$
\mathrm{CVaR}_{0.9}(T_j) = \mathbb{E}\left[T_j \mid T_j \ge \mathrm{VaR}_{0.9}(T_j)\right]
$$

$$
\mathrm{Score}_j = \mathrm{Obj}(T_j) + P_{\text{closure}} + P_{\text{delay}} + P_{\text{hyst}} + P_{\text{risk}}, \qquad
P_{\text{hyst}} = \gamma_{\text{switch}} \cdot \mathbf{1}[g_j \ne g_{\text{previous}}]
$$

| Term | Role | Setting |
| ---- | ---- | ------- |
| `P_closure` | Large constant for routes that violate hard constraints | Operating hours, capacities, boarding deadlines, accessible routes |
| `P_delay` | Penalizes expected lateness beyond the boarding deadline | η_miss held constant (see configuration files) |
| `P_hyst` | Switching penalty (hysteresis); builds stability into the decision rule | γ_switch = 1.5 |
| `P_risk` | Scales the composite congestion risk score | η_risk = 0.3 |

γ and η are **empirically calibrated conversion factors** ("score-minutes") that map dimensionless terms to the minute scale of the score; they are not physical or monetary equivalences.

### 2.4 Distributional prediction and data quality

- **Source-level reliability** = 0.5·freshness + 0.3·completeness + 0.2·response; **decision-layer quality** q = 0.4·availability + 0.4·completeness + 0.2·freshness. Weights were elicited by pairwise comparison (AHP).
- **Tiered fallback**: real-time API (reliability ≥ 0.8), recent cache under 15 min (≥ 0.6), EWMA imputation (0.4), day-of-week/time-of-day average (0.2), conservative worst-case default (0.1).
- **Ensemble**: quantile heuristic, Markov–Kalman latent-state model and Bayesian personalization component, combined by an **equal-weight average of predictive quantiles**. Stacking weights were not learned because about 36 snapshots per checkpoint are too few.
- **Blending**: ω = 1 / (1 + exp[−6(q − 0.5)]); μ_blend = ω·μ_rt + (1 − ω)·μ_ens, with the variance combined through the covariance of real-time and ensemble predictions.
- **Uncertainty inflation**: σ is inflated by (1 + λ_risk · max{0, R − R_thr}/100) with λ_risk = 0.15 and R_thr = 60.
- In deployment the covariance is estimated over a rolling 30-day window; the replay has only 36 snapshots and used the zone-level covariance from the calibration snapshots, so **the rolling estimator is specified but not exercised**.

### 2.5 Personalization

Individual heterogeneity enters through multiplicative factors on baseline walking and check-in components, estimated with a hierarchical Bayesian model that pools information across similar profiles. Incomplete profiles are imputed with population medians and their uncertainty is inflated. **The factor values are generator inputs**; the cohort-level allowances they produce are listed in [Section 12.4](#124-planning-allowance-by-cohort).

### 2.6 Policy configurations (ablation design)

Hybrid-CVaR activates all components. Because moving to it from Hybrid-Mean changes five things at once, the transition is decomposed with variants that each remove one component. "Hysteresis" and "switching penalty" are used interchangeably.

| Policy | Data integration | Objective | Hard constraints | Switching penalty | Personalization | Risk inflation |
| ------ | ---------------- | --------- | ---------------- | ----------------- | --------------- | -------------- |
| Baseline | Real-time only | Mean | No | No | No | No |
| Hybrid-Mean | Blended + ensemble | Mean | No | No | No | No |
| **Hybrid-CVaR** | Blended + ensemble | CVaR₀.₉ | Yes | γ = 1.5 | Yes | Yes |
| CVaR-NoHysteresis | Blended + ensemble | CVaR₀.₉ | Yes | γ = 0 | Yes | Yes |
| CVaR-NoPersonalization | Blended + ensemble | CVaR₀.₉ | Yes | γ = 1.5 | No | Yes |
| CVaR-NoConstraints | Blended + ensemble | CVaR₀.₉ | No | γ = 1.5 | Yes | Yes |

CVaR-NoPersonalization (generic profiles) is also the comparator for the allocation analysis. The ablation is **nested, not factorial**; the arm "CVaR-NoPersonalization with γ = 0" was not run.

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
| --------- | --------------- |
| Python | 3.10+ |
| MySQL | 8.x (or compatible, e.g., Aurora MySQL) |
| APIs | Incheon Airport Corporation (B551177) and KMA METAR service keys |
| OS | Linux/macOS/WSL2 recommended; Windows is supported |

---

## 5. Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/airport-cvar-optimization.git
   cd airport-cvar-optimization
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure environment variables.** Copy the example file and add your MySQL credentials and API keys. **Never commit `.env`.**
   ```bash
   cp .env.example .env
   nano .env
   ```

5. **Create the database**
   ```bash
   mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS icn_airport_analysis CHARACTER SET utf8mb4;"
   ```

6. **Run migrations** (idempotent; also available in `01_run_migrations.ipynb`)
   ```bash
   python -m src.db.migrations
   ```

The schema has eight tables in three domains: **operational** (`congestion_data`, `congestion_features_t1`), **predictive** (`passenger_forecast_raw`, `passenger_forecast_t1`, `metar_raw`) and **experimental** (`experiment_runs`, `experiment_metrics`, `policy_evaluation_log`). `snapshot_id` is the temporal join key; `experiment_id` and `policy_version` provide experimental traceability. Data follow a bronze (raw API responses), silver (parsed and validated, with quality annotations) and gold (feature-engineered) layering.

---

## 6. How to Run

### Mode 1: Interactive CLI

Get route recommendations for journey types Q1–Q4.

```bash
python scripts/run_interactive.py
```

### Mode 2: Automated offline replay

This script (i) collects a stream of real-time snapshots, (ii) replays every policy on **identical synthetic passengers** under identical snapshot conditions, and (iii) logs all evaluation data and summary metrics to MySQL.

```bash
# Defaults: 180 min duration, 5 min interval (= 36 snapshots)
python scripts/run_experiments.py

# Quick smoke test only; does NOT match the study design
python scripts/run_experiments.py --duration 120 --interval 5 --users 10 --epsilon 0.1
```

The reported study used **36 consecutive five-minute snapshots, 960 synthetic passengers per snapshot (34,560 journeys), compliance ε = 0.2 and random seed 42**. Set `--users 960 --epsilon 0.2` to match it.

### Mode 3: Reporting and analysis

```bash
# Replace <uuid> with the ID of the experiment run
python scripts/export_reporting.py --experiment-id <your-experiment-uuid>
```

The codebase is deterministic: with the same database snapshots and seed, experiments and analyses give identical results.

---

## 7. Generated Outputs

Running `export_reporting.py` (or `04_statistical_analysis.ipynb`) writes to `output/`. Table and figure references are to the manuscript; the mapping is indicative.

| Output | Content | Used for |
| ------ | ------- | -------- |
| `airport_experiment_results.xlsx` | Primary workbook with key tables on separate sheets | All |
| `policy_summary.csv` | Pooled APT, CVaR₀.₉, acceptance, miss rate, switch rate per policy | Table 4 |
| `Q4_metrics.csv` | Detailed Q4 (parking-to-gate) metrics | Table 6, Figs. 3–4 |
| `Q4_ci.csv` | Snapshot-level BCa bootstrap 95% intervals (B = 1,000) | Intervals throughout |
| `e1_e5_tests.csv` | Welch's t-tests, Cohen's d, Holm–Bonferroni-adjusted p-values | §5.2–5.4, Table 7 |
| `component_decomposition.csv` | Hybrid-Mean → Hybrid-CVaR decomposed into "other" (CVaR objective, constraints, switching penalty, risk inflation) and personalization, per journey type. **Path-specific**; the alternative ordering is not computed. | Table 5, Fig. 2 |
| `e6_metrics.csv` | Performance by journey type | Table B.2, Fig. B.1 |
| `cost_benefit_summary.csv`, `cost_benefit.png`, `cba_sensitivity.csv` | Passenger-side time-cost proxy (USD) and ±20% valuation sensitivity; excludes airport, airline and ground-handling costs | Table B.3 |
| `Q4_boxplot.png`, `Q4_tail_metrics.png`, `Q4_hourly_trend.png` | Journey-time distributions, tail metrics and time-of-day trend | Diagnostics |
| `propensity_overlap.png` | Propensity distribution for the common-support check | §5.6 |
| `pareto_frontier.png` | Descriptive efficiency–risk–equity view (supplementary; not part of the core attribution) | Not in the manuscript's core analysis |
| `causal_results.csv`, `causal_forest.png`, `bayesian_contrasts.csv`, `bayesian_contrast.png` | Exploratory heterogeneous-effect and Bayesian contrasts | Exploratory only |
| `figures/` | Curated publication figures | Figs. 1–5, A.1, B.1–B.2 |

**Naming note.** The BAG may appear as `equity_gap` or "Equity Gap" in output files and database fields from earlier versions. The ablation policy "CVaR-NoPersonalization" may appear as "CVaR-Generic".

---

## 8. Notebook Workflow

1. `00_environment_check.ipynb`: validate Python dependencies and database connectivity.
2. `01_run_migrations.ipynb`: execute and verify the schema setup.
3. `02_realtime_pipeline.ipynb`: walk through one cycle of ingestion and feature engineering.
4. `03_offline_replay_E1_E6.ipynb`: trigger the `ExperimentRunner` and log the experiment ID.
5. `04_statistical_analysis.ipynb`: load an experiment and run the full analysis, including the component decomposition (interactive counterpart of `export_reporting.py`).
6. `05_appendix_figures.ipynb`: generate additional visualizations, including the Pareto view and causal-effect plots.

---

## 9. Testing

```bash
# Fast unit tests
pytest

# Integration tests (require a populated database)
pytest -m integration
```

---

## 10. Data Governance and Security

- **Secrets**: credentials and API keys live only in `.env`, which is git-ignored.
- **Data**: operational inputs come from public IIAC and KMA data services under the providers' terms of service. **Redistribution of raw provider data is restricted**, so the repository contains only processed snapshot features and configuration needed to rerun the replay. Retention should be limited to 90 days. Ingested data are stored in your own MySQL database.
- **PII**: the system uses synthetic passenger profiles and handles no personally identifiable information.
- **API compliance**: ingestion uses retry with exponential backoff to respect rate limits.
- **Off-policy identification**: propensities are logged for every recommendation. Identification rests on snapshot ignorability, positivity (enforced by the ε-greedy rule; minimum observed propensity above 0.026) and SUTVA (by construction, because recommendations do not feed back into queues). Because all policies are replayed on identical simulated passengers and propensities are near uniform, **doubly robust and naive estimates agree to two decimals**. The DR pipeline is therefore a **consistency check for future live deployment, not an independent test of the policies**.

---

## 11. Evaluation Design and Verification & Validation Status

### 11.1 Replay design

- **Real**: 36 consecutive five-minute snapshots (3 hours) from IIAC and KMA streams, including departure congestion and waiting time at the 12 Terminal 1 checkpoints, ordered chronologically for a first-18 versus last-18 holdout.
- **Simulated**: 960 synthetic passengers per snapshot across seven cohorts (business travellers, standard adults, families with children, seniors, heavy-baggage travellers, passengers with reduced mobility, unaccompanied minors).
- **Compliance**: assumed ε-greedy rule (ε = 0.2), which also supplies logging propensities. It is not estimated from data and does not respond to past recommendation quality.
- **Consequences**: (i) the simulator is *model-in-the-loop*, so tail-risk benefits that depend on misspecification cannot appear and the fusion gain is partly built in; (ii) recommendations do not alter queues, so herding is not simulated; (iii) profile adjustments enter outcome sampling only under personalized policies, so the two policy classes face different true journey times.

### 11.2 Experiments

Ten experiments address the research questions; two diagnostics complement them.

| Exp | Focus | Contrast | Role |
| --- | ----- | -------- | ---- |
| **E1** | Data fusion | Baseline vs. Hybrid-Mean | Context for RQ1 (gain partly built into the simulator) |
| **E2** | Bundled policy | Hybrid-Mean vs. Hybrid-CVaR, decomposed via CVaR-NoPersonalization | RQ1 |
| **E3** | Hard constraints | Hybrid-CVaR vs. CVaR-NoConstraints | Supporting check |
| **E4** | Switching penalty | γ = 0 vs. γ = 1.5 (personalized policy) | RQ2 |
| **E5** | Personalization | Generic vs. personalized profiles | RQ3 |
| **E6** | Journey complexity | Q1 to Q4 | Face-validity check |
| **E7** | Chronological holdout | First 18 vs. last 18 snapshots | Robustness |
| **E8** | Unseen checkpoints | DG1–DG4 (calibration) vs. DG5–DG6 (test) | Robustness |
| **E9** | Weather shock | 5 mm rainfall perturbation | Exploratory |
| **E10** | Allocation | Vulnerable vs. general passengers (BAG) | RQ3 |
| **E11** | Positivity diagnostics | Logged propensity distribution | Diagnostic |
| **E13** | Parameter sensitivity | ±25% on calibrated parameters; ±10% on constraint thresholds | Diagnostic |

(E12, a descriptive Pareto view, is supplementary and outside the core attribution.)

**Statistics.** Welch's t-tests with Cohen's d for mean differences; snapshot-level BCa bootstrap intervals for tail quantities; Fisher's exact tests for binary outcomes; Holm–Bonferroni control across E1–E10; all intervals 95%. Metric definitions: **APT** (mean journey time), **Q90**, **CVaR₀.₉**, **miss rate** (share of journeys missing the boarding deadline), **acceptance rate** (determined by the assumed compliance rule in the replay), **switch rate** (share of recommendations that differ from the same passenger's previous-cycle recommendation), **BAG**.

### 11.3 What the replay verifies and what it does not validate

| Item | Status | Evidence and limitation |
| ---- | ------ | ----------------------- |
| Exact reproducibility | Verified | `snapshot_id` lineage and fixed seed (42) |
| Monte Carlo sample size | Verified | CVaR estimates stabilize (CV < 2%) at N ≥ 150; N = 200 runs in under 0.8 s per cycle |
| Hard-constraint handling | Verified by contrast | 0 violations vs. 2,362 (6.83%) without constraints; zero holds by construction |
| Positivity and estimator agreement | Checked | Minimum propensity above 0.026; DR and naive agree to two decimals |
| Parameter sensitivity | **Partly checked** | ±25% on calibrated parameters (spread of APT and CVaR₀.₉ reported); **policy ranking and sign of the switching effect not examined**; ±10% on constraint thresholds (zero violations preserved) |
| Input snapshots | Real data | IIAC and KMA streams; short window |
| Journey-time distributions | **Not validated** | Not compared with observed passenger journeys; parking-search model consistent with literature but not with measured search times |
| Passenger compliance | **Assumed** | ε = 0.2; no sensitivity analysis performed |
| Personalization factors | Generator inputs | Effects are conditional on the generator's profile model |
| Queue feedback | **Absent** | Effects of switching on queues and herding cannot be observed |
| Scalability | Partly tested | 12 Terminal 1 checkpoints under 0.8 s per cycle; larger networks untested |

---

## 12. Key Results

From 34,560 simulated journeys across 36 snapshots. Intervals are 95% snapshot-level bootstrap intervals. Contrasts labeled Q4 refer to the parking-to-gate scenario; other values are pooled.

### 12.1 Pooled policy performance

| Policy | APT (min) [95% CI] | CVaR₀.₉ (min) | Acceptance (%) | Miss rate (%) |
| ------ | ------------------ | ------------- | -------------- | ------------- |
| Baseline | 37.18 [37.01, 37.35] | 48.95 | 80.6 | 0.00 |
| Hybrid-Mean | 37.15 [36.99, 37.31] | 47.17 | 79.7 | 0.00 |
| **Hybrid-CVaR** | 43.51 [43.26, 43.76] | 62.39 | 79.1 | 0.40 |
| CVaR-NoHysteresis | 43.50 [43.25, 43.75] | 62.93 | 80.8 | 0.52 |
| CVaR-NoPersonalization | 37.23 [37.07, 37.39] | 47.17 | 80.5 | 0.00 |

_Acceptance follows the assumed ε-greedy rule and is reported for completeness; it is not an outcome of passenger behavior._

Two regimes emerge. Hybrid-CVaR **raises** pooled APT by 6.36 min (17.1%) and CVaR₀.₉ by 15.22 min relative to Hybrid-Mean. CVaR-NoPersonalization returns to Hybrid-Mean levels, so the increase comes from personalization. The framework does **not** lower nominal tail risk relative to Hybrid-Mean, and no tail-risk gain is credited to the CVaR objective (offsetting individual effects cannot be excluded because components were not removed one at a time).

### 12.2 RQ1: which lever carries the recommended-time cost?

Decomposition of the Hybrid-Mean → Hybrid-CVaR change (minutes; "Other" = CVaR objective, hard constraints, switching penalty and risk inflation):

| Journey type | ΔAPT | Other | Personalization (share) | ΔCVaR₀.₉ | Other | Personalization (share) |
| ------------ | ---- | ----- | ----------------------- | -------- | ----- | ----------------------- |
| Q1 Check-in to gate | +4.318 | +0.152 | +4.166 (96.5%) | +7.952 | +0.121 | +7.831 (98.5%) |
| Q2 Rail to gate | +6.957 | −0.026 | +6.983 (100.4%) | +14.098 | −0.141 | +14.239 (101.0%) |
| Q3 Curbside to gate | +5.094 | −0.003 | +5.097 (100.1%) | +9.246 | +0.342 | +8.904 (96.3%) |
| Q4 Parking to gate | +7.722 | +0.150 | +7.572 (98.1%) | +16.523 | −0.065 | +16.588 (100.4%) |

- Q4 (E2): +7.72 min (18.4%; 95% CI 6.51 to 8.89; d = 1.17; p < 0.001); miss rate rises from 0.00% to 0.82% (95% CI 0.51 to 1.13), likewise tied to personalization.
- Shares above or below 100% reflect offsetting contributions of the other components.
- The attribution follows **one path** (Hybrid-Mean → CVaR-NoPersonalization → Hybrid-CVaR); interactions may be present and the alternative ordering was not computed.
- Data fusion (E1, Q4): mean time −0.21 min (p = 0.097, n.s.), Q90 −1.88 min and switch rate 75.7% → 64.9% (both p < 0.001); partly built into the simulator.

### 12.3 RQ2: what governs recommendation stability?

| Q4 configuration | CVaR bundle | Personalization | Switching penalty | APT (min) | CVaR₀.₉ (min) | Switch rate (%) |
| ---------------- | ----------- | --------------- | ----------------- | --------- | ------------- | --------------- |
| Hybrid-Mean | No | No | No | 41.89 | n/a | 64.9 |
| CVaR-NoPersonalization | Yes | No | Yes | 42.04 (derived: 49.61 − 7.57) | n/a | 80.0 |
| CVaR-NoHysteresis | Yes | Yes | No | 49.57 | 66.58 | 59.1 |
| **Hybrid-CVaR** | Yes | Yes | Yes | 49.61 | 66.04 | **26.0** |

The "CVaR bundle" is the CVaR objective, hard constraints and risk inflation switched on together.

- Within the personalized policy the penalty cuts switching from 59.1% to 26.0% (56.0% relative reduction) with no significant change in mean time (+0.05 min; p = 0.740) or CVaR₀.₉ (p = 0.312).
- Without personalization the penalty's effect is **not identified** (no γ = 0 arm); the rise from 64.9% to 80.0% reflects the CVaR bundle and the penalty together and is unexplained. The claim is only that the **combination is associated with** the reduction.
- One untested explanation: personalization changes the spread of route scores so that a fixed penalty becomes comparable to score differences between routes.
- Pooled acceptance moves from 80.8% to 79.1% (nominal p = 0.042), but acceptance is fixed by the assumed compliance rule and is **not evidence on passenger acceptance**; measuring it requires a field trial.

### 12.4 RQ3: how is planning allowance allocated?

**Personalization effects on journey time (E5, doubly robust):**

| Journey type | ATE [95% CI] (min) | Cohen's d |
| ------------ | ------------------ | --------- |
| Q1 Check-in to gate | +4.17 [3.49, 4.80] | 1.31 |
| Q2 Rail to gate | +7.01 [5.85, 8.14] | 1.27 |
| Q3 Curbside to gate | +5.09 [4.30, 5.89] | 1.12 |
| Q4 Parking to gate | +7.58 [6.38, 8.75] | 1.15 |

All p < 0.001. Because the direction follows from the generator's profile model, these effects quantify the buffer allocated.

**Planning allowance by cohort (generator inputs, relative to the generic profile):**

| Cohort | Mean allowance (min) | Vulnerable |
| ------ | -------------------- | ---------- |
| Business travellers | +1.8 | No |
| Standard adults | +2.1 | No |
| Heavy-baggage travellers | +6.7 | No |
| Senior passengers | +8.4 | Yes |
| Families with children | +9.1 | Yes |
| Passengers with reduced mobility | +12.3 | Yes |
| Unaccompanied minors | +15.2 | Yes |

Allowances scale with the length of the walking and check-in components, so values vary by journey type.

**BAG by policy (Q4, E10):** Hybrid-Mean 0.03 · CVaR-NoPersonalization 0.04 · **Hybrid-CVaR 7.83 min**. As a consistency check of Remark 1, with ATE = 7.58 and Δ₀ ≈ 0.03, the implied general-cohort allowance ā_G ≈ 7.58 − 7.80w lies within the cohort range (+1.8 to +6.7 min) if and only if the vulnerable share w is between about 0.11 and 0.74. The check is approximate and tests the simulator, not real passengers.

Two features qualify the single number: heavy-baggage travellers (no vulnerability criterion) receive +6.7 min yet are counted as general, which lowers the BAG; and the BAG is silent on allocation within the vulnerable group (+8.4 for seniors to +15.2 for unaccompanied minors).

### 12.5 Constraints, robustness and cost

- **Hard constraints (E3)**: 0 violations under Hybrid-CVaR (by construction) vs. 2,362 infeasible recommendations (6.83%) under CVaR-NoConstraints; zero violations persist under ±10% threshold perturbations.
- **Journey complexity (E6)**: APT/CVaR₀.₉ are lowest for Q1 (32.55 / 39.83 min) and highest for Q4 (47.07 / 64.57); the two-stage order is Q3 < Q2 < Q4, so stage count alone does not explain it. Face-validity check only.
- **Holdout and unseen checkpoints (E7, E8)**: CVaR₀.₉ drifted by less than 0.1% between the first and last 18 snapshots; on unseen checkpoints DG5–DG6 CVaR₀.₉ = 60.7 min with no violations, and the recommendation distribution shifted (KL = 0.770; appropriateness not assessed).
- **Weather shock (E9, exploratory)**: a 5 mm rainfall shock raised CVaR₀.₉ by 4.53 min for Hybrid-CVaR (+9.3%; miss rate 0.90%) and 3.92 min for Hybrid-Mean (+10.0%; miss rate 0.00%). Because personalization raises the unperturbed level and the test lacks CVaR-NoPersonalization and multiple shock magnitudes, the smaller relative rise **cannot be attributed to the CVaR objective**. The shock replay uses a separate set (unperturbed levels about 48.7 and 39.2 min), so levels are not comparable with Section 12.1.
- **Passenger-side time cost**: relative to Baseline (USD 24.74 per observation), Hybrid-Mean is USD 0.22 cheaper and Hybrid-CVaR USD 3.39 more expensive, mainly reflecting the buffer allocated through personalization. The ordering is unchanged under ±20% valuation perturbations. Cost components were not decomposed, so this is not read as a monetary value of stabilization.
- **Sensitivity (E13)**: ±25% perturbation of calibrated parameters gives variance 0.075 min² (APT) and 0.284 min² (CVaR₀.₉), i.e. standard deviations of about 0.27 and 0.53 min. Whether policy ranking and the sign of the switching effect are preserved was **not examined**.

### 12.6 What is and is not established

| Question | Established in the replay | Not established |
| -------- | ------------------------- | --------------- |
| Where does the recommended-time cost come from? | Personalization (96.5–100.4% of the APT increase, path-specific) | Whether the allowances match real passenger needs |
| What stabilizes recommendations? | The penalty within the personalized policy (59.1% → 26.0%) | The separate roles of penalty and personalization; effects on queues and trust |
| Does the CVaR objective help? | No standalone effect under nominal conditions | Any benefit under stress or misspecification (the design cannot isolate it) |
| Are operating limits respected? | 0 violations (by construction); 6.83% infeasible without constraints | Behavior under real rule changes |
| How is allowance allocated? | BAG 0.03 → 7.83 min, traceable to personalization | An appropriate target level; real-population equity |

---

## 13. Implications for Operators and Staged Validation

These are proposals derived from a simulation, **not** descriptions of current regulation or of any airport's practice.

### 13.1 Constraints-first order of decisions (motivated by the replay, not tested by it)

1. **Hard operating constraints are non-negotiable** and are verified before any comparison (they removed the 6.83% of otherwise infeasible recommendations).
2. **Set personalization strength as an explicit service-standard decision**, with segment allowances calibrated against measured processing times and its mean-time cost and miss rate reviewed together.
3. **Monitor the BAG by segment** against a need-based reference; prefer a two-sided corridor to a one-sided cap (untested). The aggregate BAG is a first-level screen only.
4. **Tune the switching penalty and any tail-risk objective last**, and adopt them only if shadow-mode divergence and tail outcomes warrant it.

### 13.2 Staged route from replay to operation

| Stage | Purpose | Decision gate |
| ----- | ------- | ------------- |
| 0. Offline replay (this repository) | Attribute component effects | Proceed to validation only; no operational claim |
| 1. Generator validation | Compare simulated journey-time distributions and compliance with observed journeys; test sensitivity to the compliance rule | Recalibrate personalization factors; stop if distributions diverge materially |
| 2. Shadow mode | Log recommendations without showing them; compute switch rate, decision-divergence rate and BAG against a need-based reference, including a period with adverse weather | Proceed if behavior resembles the replay; otherwise retune γ and allowances |
| 3. Controlled field trial | Show recommendations to opt-in passengers at selected checkpoints with a holdout group | Expand only on pre-registered criteria |
| 4. Network operation | Scale to all 12 checkpoints with drift and equity dashboards | Periodic recalibration |

---

## 14. Limitations and Research Agenda

**Limitations.** (1) All results come from offline replay with synthetic passengers under an assumed compliance rule; journey times are not validated against observed ones. (2) The data are 36 five-minute snapshots from one terminal; seasonal and long-run drift are not assessed. (3) The ablation is nested, not factorial: the standalone effect of the tail-risk objective and the penalty's effect without personalization are not identified, and interactions cannot be quantified. (4) Stress evidence rests on one shock type and magnitude. (5) The BAG is a mean difference; miss rates and realized times are not broken down by vulnerable and general passengers, and the cost analysis covers passenger-side time only. Zero-violation and positivity results hold by construction.

**Priority extensions (not implemented in this repository).**

- (a) A **personalization-strength sweep** that converts the single-point cost into a price-of-allowance frontier (mean time, miss rate and BAG as the allowance scale moves from zero to the generator value);
- (b) a segment-level decomposition of the miss rate;
- (c) a full factorial design crossing objective, personalization and switching penalty, including the missing CVaR-NoPersonalization arm with γ = 0;
- (d) stress tests including CVaR-NoPersonalization across shock magnitudes;
- (e) sensitivity to the compliance rule and to the calibrated parameters, reporting whether policy ranking and the sign of the switching effect are preserved;
- (f) shadow-mode validation (Stage 2 above), including a decision-divergence rate (share of decisions where the mean and CVaR objectives choose different routes).

---

## 15. License

This project is licensed under the MIT License. See the `LICENSE` file for details.
