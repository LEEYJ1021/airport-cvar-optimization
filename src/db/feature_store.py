from __future__ import annotations

from datetime import datetime
import logging
from typing import Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("airport.db.feature_store")


class FeatureStore:
    """
    Provides a read-only interface to access pre-computed or static features
    stored in the database, such as weather, holidays, or flight schedules.
    This helps decouple the main optimization logic from data source details.
    """

    def __init__(self, engine: Engine):
        """
        Initializes the FeatureStore with a SQLAlchemy engine.

        Args:
            engine: The SQLAlchemy engine for database connections.
        """
        self.engine = engine

    def get_schedule_density(self, hour_of_week: int) -> Optional[int]:
        """
        Retrieves the scheduled departure density for a given hour of the week.

        Args:
            hour_of_week: The hour of the week (0-167).

        Returns:
            The number of scheduled departures, or None if not found.
        """
        query = text(
            "SELECT departures FROM schedule_density WHERE hour_of_week = :how LIMIT 1;"
        )
        try:
            with self.engine.connect() as conn:
                row = conn.execute(query, {"how": hour_of_week}).fetchone()
                return int(row[0]) if row else None
        except SQLAlchemyError as e:
            logger.warning(f"Could not fetch schedule density for hour {hour_of_week}: {e}")
            return None

    def get_weather_hourly(
        self, dt: datetime
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Retrieves hourly weather data (temperature and rain) for a given timestamp.

        Args:
            dt: The datetime to query. It will be normalized to the start of the hour.

        Returns:
            A tuple of (temperature, rain_mm), or (None, None) if not found.
        """
        normalized_ts = dt.replace(minute=0, second=0, microsecond=0)
        query = text("SELECT temp, rain FROM weather_hourly WHERE ts = :ts LIMIT 1;")
        try:
            with self.engine.connect() as conn:
                row = conn.execute(query, {"ts": normalized_ts}).fetchone()
                if row:
                    return float(row[0]), float(row[1])
                return None, None
        except SQLAlchemyError as e:
            logger.warning(f"Could not fetch hourly weather for {normalized_ts}: {e}")
            return None, None

    def is_holiday(self, dt: datetime) -> int:
        """
        Checks if a given date is a holiday from the holiday calendar.

        Args:
            dt: The datetime to check.

        Returns:
            1 if it is a holiday, 0 otherwise. Returns 0 on error.
        """
        query = text("SELECT is_holiday FROM holiday_calendar WHERE date = :d LIMIT 1;")
        try:
            with self.engine.connect() as conn:
                row = conn.execute(query, {"d": dt.date()}).fetchone()
                return int(row[0]) if row else 0
        except SQLAlchemyError as e:
            logger.warning(f"Could not check holiday status for {dt.date()}: {e}")
            return 0