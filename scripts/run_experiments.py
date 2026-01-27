#!/usr/bin/env python
import logging

import typer

from src.pipeline.cli import run_experiments_command

logger = logging.getLogger("airport.scripts")

# We use typer's runner to handle CLI arguments gracefully
cli_app = typer.Typer()
cli_app.command()(run_experiments_command)

if __name__ == "__main__":
    logger.info("Starting script: run_experiments.py")
    try:
        cli_app()
    except Exception as e:
        logger.critical(f"An unhandled exception occurred in run_experiments: {e}", exc_info=True)
    logger.info("Finished script: run_experiments.py")