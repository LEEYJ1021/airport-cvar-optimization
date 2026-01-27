from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

import pandas as pd

logger = logging.getLogger("airport.analytics.tables")


class TableExporter:
    """
    A utility class for exporting analysis results to various file formats.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

    def export_all(self, results: Dict[str, pd.DataFrame], excel_filename: str):
        """
        Exports all result DataFrames to a single Excel file with multiple sheets
        and also as individual CSV files.

        Args:
            results: A dictionary where keys are sheet/file names and values are DataFrames.
            excel_filename: The name for the output Excel file.
        """
        excel_path = self.output_dir / excel_filename
        try:
            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                for name, df in results.items():
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        df.to_excel(writer, sheet_name=name, index=False)
                        logger.info(f"Wrote sheet '{name}' to {excel_path}")
                        
                        # Also save as CSV
                        csv_path = self.output_dir / f"{name}.csv"
                        df.to_csv(csv_path, index=False)
                        logger.info(f"Saved CSV file: {csv_path}")

            logger.info(f"✅ Successfully exported all results to {excel_path}")
        except Exception as e:
            logger.error(f"❌ Failed to export results to Excel: {e}")

    def to_latex(self, df: pd.DataFrame, caption: str, label: str) -> str:
        """
        Generates a LaTeX table from a DataFrame.

        Args:
            df: The DataFrame to convert.
            caption: The table caption.
            label: The LaTeX label for cross-referencing.

        Returns:
            A string containing the LaTeX table code.
        """
        if df.empty:
            return "% DataFrame is empty, no table generated."
            
        try:
            latex_str = df.to_latex(
                index=False,
                caption=caption,
                label=label,
                float_format="%.2f",
                header=True,
                escape=True,
            )
            logger.info(f"Generated LaTeX table with caption: '{caption}'")
            return latex_str
        except Exception as e:
            logger.error(f"Failed to generate LaTeX table: {e}")
            return f"% Error generating LaTeX table: {e}"