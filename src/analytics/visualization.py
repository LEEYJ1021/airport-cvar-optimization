from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

logger = logging.getLogger("airport.analytics.viz")


class FigureGenerator:
    """
    Generates and saves publication-quality figures from analysis results.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        sns.set_theme(style="whitegrid", palette="viridis")

    def _save_plot(self, filename: str):
        """Helper to save the current plot to a file."""
        path = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved figure: {path}")

    def plot_q4_boxplots(self, df_log: pd.DataFrame):
        """Plots boxplots of total travel time for Q4 by policy."""
        df_q4 = df_log[df_log["scenario"] == "Q4"].copy()
        if df_q4.empty:
            logger.warning("No data for Q4, skipping boxplot.")
            return
            
        plt.figure(figsize=(10, 6))
        sns.boxplot(data=df_q4, x="policy_group", y="realized_total", showfliers=False)
        plt.title("Q4: Total Travel Time Distribution by Policy", fontsize=16)
        plt.xlabel("Policy Group", fontsize=12)
        plt.ylabel("Total Time (minutes)", fontsize=12)
        plt.xticks(rotation=30, ha="right")
        self._save_plot("q4_travel_time_boxplot.png")

    def plot_q4_tail_risk(self, df_q4_metrics: pd.DataFrame):
        """Plots a bar chart of tail risk metrics (Q90, CVaR) for Q4."""
        if df_q4_metrics.empty:
            logger.warning("No Q4 metrics, skipping tail risk plot.")
            return

        df_melt = df_q4_metrics.melt(
            id_vars="policy_group",
            value_vars=["Q90", "CVaR_0.9"],
            var_name="Metric",
            value_name="Time (minutes)",
        )
        
        plt.figure(figsize=(10, 6))
        sns.barplot(data=df_melt, x="policy_group", y="Time (minutes)", hue="Metric")
        plt.title("Q4: Tail Risk Metrics by Policy", fontsize=16)
        plt.xlabel("Policy Group", fontsize=12)
        plt.ylabel("Time (minutes)", fontsize=12)
        plt.xticks(rotation=30, ha="right")
        plt.legend(title="Metric")
        self._save_plot("q4_tail_risk_barchart.png")

    def plot_e6_cvar(self, df_e6_metrics: pd.DataFrame):
        """Plots a bar chart of CVaR for the main policy across different scenarios."""
        if df_e6_metrics.empty:
            logger.warning("No E6 metrics, skipping CVaR by scenario plot.")
            return
            
        plt.figure(figsize=(8, 5))
        sns.barplot(data=df_e6_metrics, x="scenario", y="CVaR_0.9", color=sns.color_palette("viridis")[3])
        plt.title("E6: CVaR by Scenario (for Hybrid-CVaR Policy)", fontsize=16)
        plt.xlabel("Scenario", fontsize=12)
        plt.ylabel("CVaR (minutes)", fontsize=12)
        self._save_plot("e6_cvar_by_scenario.png")