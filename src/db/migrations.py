from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.db.engine import get_engine
from src.settings import BASE_DIR, get_config

logger = logging.getLogger("airport.db.migrations")

# Load SQL statements from files
SQL_DIR = BASE_DIR / "sql"
try:
    CREATE_TABLE_SQL = (
        (SQL_DIR / "00_create_schema.sql").read_text(encoding="utf-8").split(";")
    )
    ALTER_TABLE_SQL = (
        (SQL_DIR / "01_alter_columns.sql").read_text(encoding="utf-8").split(";")
    )
except FileNotFoundError as e:
    logger.error(f"SQL migration file not found: {e}")
    CREATE_TABLE_SQL = []
    ALTER_TABLE_SQL = []


def _execute_statements(statements: list[str], conn) -> None:
    """Helper to execute a list of SQL statements within a transaction."""
    for stmt in statements:
        s = stmt.strip()
        if s:
            try:
                conn.execute(text(s))
                logger.debug(f"Executed: {s[:80]}...")
            except SQLAlchemyError as e:
                # Log warnings for common idempotent errors, but don't fail
                if "Duplicate column name" in str(e) or "already exists" in str(e):
                    logger.warning(f"Idempotent DDL warning: {e}")
                else:
                    logger.error(f"Error executing statement: {s}\n{e}")
                    raise


def run_migrations() -> None:
    """
    Runs all defined database migrations (CREATE and ALTER).
    This function is idempotent and safe to run on an existing database.
    """
    logger.info("Starting database migrations...")
    engine = get_engine()
    try:
        with engine.begin() as conn:
            logger.info("Running CREATE TABLE statements...")
            _execute_statements(CREATE_TABLE_SQL, conn)
            logger.info("Running ALTER TABLE statements...")
            _execute_statements(ALTER_TABLE_SQL, conn)
        logger.info("✅ Database migrations completed successfully.")
    except Exception as e:
        logger.critical(f"❌ A critical error occurred during migrations: {e}")
        raise


if __name__ == "__main__":
    # This allows running migrations directly from the command line.
    print("Running migrations as a standalone script...")
    run_migrations()
    print("Finished.")