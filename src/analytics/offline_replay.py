from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as st
from statsmodels.stats.multitest import multipletests

from src.analytics.tables import TableExporter
from src.analytics.visualization import FigureGenerator
from src.db import get_engine
from src.utils.helpers import compute_cvar

logger = logging.getLogger("airport.analytics.replay")


class OfflineReplayAnalyzer:
    """
    A class to perform a full analysis of offline experiment results.
    It loads data, computes metrics, performs statistical tests, and exports reports.
    """

    def __init__(self, experiment_id: str, use_db: bool = True):
        self.experiment_id = experiment_id
        self.use_db = use_db
        self.engine = get_engine() if use_db else None
        self.df_log: pd.DataFrame | None = None
        self.results: Dict[str, pd.DataFrame] = {}

    def run_full_pipeline(self, output_dir: str = "output"):
        """
        Executes the entire analysis pipeline from data loading to exporting results.

        Args:
            output_dir: The directory to save output files.
        """
        logger.info(f"Starting analysis pipeline for experiment ID: {self.experiment_id}")
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # 1. Load and prepare data
        self.load_data()
        self.prepare_data()

        # 2. Compute primary metrics
        self.results["q4_metrics"] = self._analyze_q4_performance()
        self.results["e6_metrics"] = self._analyze_e6_performance()

        # 3. Perform statistical analysis
        self.results["q4_ci"] = self._bootstrap_ci_analysis()
        self.results["e1_e5_tests"], p_values = self._run_e1_e5_tests()
        if p_values:
            self._apply_holm_bonferroni(p_values)

        # 4. Generate summary tables
        self.results["policy_summary"] = self._generate_policy_summary()
        
        # 5. Export results
        exporter = TableExporter(output_path)
        exporter.export_all(self.results, f"experiment_results_{self.experiment_id}.xlsx")

        # 6. Generate visualizations
        viz = FigureGenerator(output_path)
        if "q4_metrics" in self.results:
            viz.plot_q4_boxplots(self.df_log)
            viz.plot_q4_tail_risk(self.results["q4_metrics"])
        if "e6_metrics" in self.results:
            viz.plot_e6_cvar(self.results["e6_metrics"])
        
        logger.info("✅ Analysis pipeline completed successfully.")

    def load_data(self):
        """Loads policy evaluation logs from the database."""
        if not self.use_db or not self.engine:
            raise ConnectionError("Database connection is not available.")
        
        query = "SELECT * FROM policy_evaluation_log WHERE experiment_id = :eid"
        try:
            self.df_log = pd.read_sql(query, self.engine, params={"eid": self.experiment_id})
            if self.df_log.empty:
                raise ValueError(f"No data found for experiment_id '{self.experiment_id}'")
            logger.info(f"Loaded {len(self.df_log)} log entries from the database.")
        except Exception as e:
            logger.error(f"Failed to load data from DB: {e}")
            raise

    def prepare_data(self):
        """Cleans data and creates derived columns for analysis."""
        df = self.df_log
        df["accepted"] = df["accepted"].astype(int)
        df["missed"] = df["missed"].astype(int)
        df["policy_group"] = df["policy_version"].str.replace(r"^v\d+\.\d+(\.\d+)?-", "", regex=True)
        df["is_hcvar"] = df["policy_version"].str.contains("cvar").astype(int)
        self.df_log = df

    def _summarize_metrics(self, df_sub: pd.DataFrame) -> Dict:
        """Computes a standard set of performance metrics for a dataframe slice."""
        vals = df_sub["realized_total"].dropna().values
        if len(vals) == 0:
            return {"n": 0, "APT_mean": np.nan, "Q90": np.nan, "CVaR_0.9": np.nan, "MissRate": np.nan}
        return {
            "n": len(vals),
            "APT_mean": float(np.mean(vals)),
            "Q90": float(np.quantile(vals, 0.9)),
            "CVaR_0.9": compute_cvar(vals, 0.9),
            "MissRate": float(df_sub["missed"].mean()),
            "AcceptanceRate": float(df_sub["accepted"].mean()),
            "SD": float(np.std(vals, ddof=1)),
        }

    def _analyze_q4_performance(self) -> pd.DataFrame:
        df_q4 = self.df_log[self.df_log["scenario"] == "Q4"]
        return df_q4.groupby("policy_group").apply(
            lambda g: pd.Series(self._summarize_metrics(g))
        ).reset_index().sort_values("APT_mean")

    def _analyze_e6_performance(self) -> pd.DataFrame:
        df_hcvar = self.df_log[self.df_log["is_hcvar"] == 1]
        return df_hcvar.groupby("scenario").apply(
            lambda g: pd.Series(self._summarize_metrics(g))
        ).reset_index().sort_values("APT_mean")

    def _bootstrap_ci(self, values, func=np.mean, n_boot=1000, alpha=0.05):
        rng = np.random.default_rng(42)
        stats = [func(rng.choice(values, size=len(values), replace=True)) for _ in range(n_boot)]
        return (np.quantile(stats, alpha / 2), np.quantile(stats, 1 - alpha / 2))

    def _bootstrap_ci_analysis(self) -> pd.DataFrame:
        df_q4 = self.df_log[self.df_log["scenario"] == "Q4"]
        rows = []
        for pol, g in df_q4.groupby("policy_group"):
            vals = g["realized_total"].dropna().values
            if len(vals) > 10:
                rows.append({
                    "policy_group": pol, "n": len(vals),
                    "mean_ci": self._bootstrap_ci(vals, np.mean),
                    "cvar_ci": self._bootstrap_ci(vals, lambda x: compute_cvar(x, 0.9)),
                })
        return pd.DataFrame(rows)

    def _run_e1_e5_tests(self) -> Tuple[pd.DataFrame, list]:
        experiments = {
            "E1": ("baseline", "hmean"), "E2": ("hmean", "cvar"), "E4": ("cvar-nohys", "cvar"), "E5": ("cvar-nopers", "cvar")
        }
        results, p_values = [], []
        df_q4 = self.df_log[self.df_log["scenario"] == "Q4"]
        
        for code, (p1_stem, p2_stem) in experiments.items():
            df1 = df_q4[df_q4["policy_group"] == p1_stem]
            df2 = df_q4[df_q4["policy_group"] == p2_stem]
            if df1.empty or df2.empty: continue
            
            v1, v2 = df1["realized_total"].dropna(), df2["realized_total"].dropna()
            if len(v1) < 10 or len(v2) < 10: continue

            t_stat, p_val = st.ttest_ind(v1, v2, equal_var=False)
            d = (np.mean(v2) - np.mean(v1)) / np.sqrt((np.var(v1, ddof=1) + np.var(v2, ddof=1)) / 2)
            
            results.append({
                "experiment": code, "policy1": p1_stem, "policy2": p2_stem,
                "n1": len(v1), "n2": len(v2), "apt1": np.mean(v1), "apt2": np.mean(v2),
                "improvement_pct": (np.mean(v1) - np.mean(v2)) / np.mean(v1) * 100,
                "t_stat": t_stat, "p_value": p_val, "cohens_d": d,
            })
            p_values.append(p_val)
        return pd.DataFrame(results), p_values

    def _apply_holm_bonferroni(self, p_values: list):
        """Applies Holm-Bonferroni correction to p-values in the results DataFrame."""
        df_tests = self.results["e1_e5_tests"]
        if not p_values or df_tests.empty: return
        
        rejected, p_corrected, _, _ = multipletests(p_values, alpha=0.05, method='holm')
        df_tests["p_corrected"] = p_corrected
        df_tests["significant_05"] = rejected
        self.results["e1_e5_tests"] = df_tests

    def _generate_policy_summary(self) -> pd.DataFrame:
        """Creates a summary table with switch rates for each policy."""
        def switch_rate(df_group):
            df_sorted = df_group.sort_values("ts")
            if len(df_sorted) <= 1: return 0.0
            switches = (df_sorted["recommended_gate"].shift() != df_sorted["recommended_gate"]).sum()
            return switches / (len(df_sorted) - 1)

        summary = self.df_log.groupby("policy_group").apply(lambda g: pd.Series({
            **self._summarize_metrics(g),
            "switch_rate": switch_rate(g)
        })).reset_index()
        return summary