#!/usr/bin/env python
import logging

from src.pipeline.cli import run_interactive

logger = logging.getLogger("airport.scripts")

if __name__ == "__main__":
    logger.info("Starting script: run_interactive.py")
    try:
        run_interactive()
    except Exception as e:
        logger.critical(f"An unhandled exception occurred in run_interactive: {e}", exc_info=True)
    logger.info("Finished script: run_interactive.py")