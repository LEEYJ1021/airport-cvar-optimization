from __future__ import annotations

import logging
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.settings import get_config

logger = logging.getLogger("airport.db.engine")

_engine: Engine | None = None


def get_engine(echo: bool = False) -> Engine:
    """
    Creates and returns a singleton SQLAlchemy Engine instance.

    Args:
        echo: If True, the engine will log all statements.

    Returns:
        A SQLAlchemy Engine instance.
    """
    global _engine
    if _engine is not None:
        return _engine

    cfg = get_config()
    try:
        encoded_pwd = quote_plus(cfg["mysql_password"])
        uri = (
            f"mysql+pymysql://{cfg['mysql_user']}:{encoded_pwd}"
            f"@{cfg['mysql_host']}:{cfg['mysql_port']}/{cfg['mysql_db']}?charset=utf8mb4"
        )
        _engine = create_engine(
            uri, pool_pre_ping=True, pool_recycle=3600, echo=echo
        )
        logger.info("Successfully created SQLAlchemy engine.")
        return _engine
    except Exception as e:
        logger.error(f"Failed to create SQLAlchemy engine: {e}")
        raise


class DBWriter:
    """A utility class for writing pandas DataFrames to the database."""

    def __init__(self, engine: Engine):
        """
        Initializes the DBWriter with a SQLAlchemy engine.

        Args:
            engine: The SQLAlchemy engine to use for database connections.
        """
        self.engine = engine

    def insert_df(self, table_name: str, df: pd.DataFrame):
        """
        Inserts a DataFrame into the specified database table.

        Args:
            table_name: The name of the target table.
            df: The pandas DataFrame to insert.
        """
        if df is None or df.empty:
            logger.debug(f"Skipping insert into '{table_name}' as DataFrame is empty.")
            return
        try:
            df.to_sql(table_name, con=self.engine, if_exists="append", index=False)
            logger.info(f"Inserted {len(df)} rows into '{table_name}'.")
        except Exception as e:
            logger.error(f"Failed to insert DataFrame into '{table_name}': {e}")
            # Depending on the use case, you might want to re-raise the exception
            # raise e