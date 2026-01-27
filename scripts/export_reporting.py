#!/usr/bin/env python
import logging

import typer

from src.analytics.offline_replay import OfflineReplayAnalyzer

logger = logging.getLogger("airport.scripts")


def main(
    experiment_id: str = typer.Option(..., "--experiment-id", "-e", help="The UUID of the experiment to analyze."),
    output_dir: str = typer.Option("output", "--output-dir", "-o", help="Directory to save the report files."),
):
    """
    Generates a full statistical report from a completed experiment run.
    """
    typer.secho(f"Starting report generation for experiment: {experiment_id}", fg=typer.colors.YELLOW)
    logger.info(f"Starting report generation for experiment: {experiment_id}")
    try:
        analyzer = OfflineReplayAnalyzer(experiment_id=experiment_id)
        analyzer.run_full_pipeline(output_dir=output_dir)
        typer.secho(f"✅ Report successfully generated in '{output_dir}/'", fg=typer.colors.GREEN)
    except Exception as e:
        logger.critical(f"Report generation failed: {e}", exc_info=True)
        typer.secho(f"❌ Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    typer.run(main)