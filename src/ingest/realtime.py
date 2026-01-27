from __future__ import annotations

import json
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import requests

from src.db.engine import DBWriter
from src.db.feature_store import FeatureStore
from src.settings import (
    GATES_T1, TERMINAL_ID, TERMINAL_NAME, get_config, get_service_key
)
from src.utils.helpers import clamp, hour_of_week, winsorize

logger = logging.getLogger("airport.ingest.realtime")


@dataclass
class CongestionSnapshot:
    """
    A dataclass representing a snapshot of airport congestion at a specific time.
    It includes both raw API data and derived contextual features.
    """
    gate_wait: Dict[str, float]
    gate_length: Dict[str, int]
    source: str
    collected_at: datetime
    quality_score: float
    quality_pred_based: float
    raw_count: int
    fallback_level: int
    snapshot_id: str
    hour_of_week: int
    raw_items: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    is_holiday: int | None = None
    schedule_density: float | None = None
    weather_temp: float | None = None
    weather_rain: float | None = None


class RealtimeCongestionClient:
    """
    A client for fetching real-time congestion data from the Incheon Airport API.
    Includes retry logic with exponential backoff.
    """

    def __init__(self, timeout: int = 8, max_retries: int = 2, backoff_factor: float = 0.8):
        self.api_url = "https://apis.data.go.kr/B551177/statusOfDepartureCongestion/getDepartureCongestion"
        self.service_key = get_service_key('default')
        self.session = requests.Session()
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def fetch_gate_data(self, gate_id: str) -> Dict[str, Any] | None:
        """
        Fetches congestion data for a single gate.

        Args:
            gate_id: The ID of the gate to query (e.g., 'DG1_W').

        Returns:
            A dictionary containing the API response item, or None on failure.
        """
        params = {
            "serviceKey": self.service_key,
            "pageNo": 1,
            "numOfRows": 1,
            "terminalId": TERMINAL_ID,
            "gateId": gate_id.split("_")[0], # API uses 'DG1', not 'DG1_W'
            "type": "json"
        }
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(self.api_url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                items = data.get("response", {}).get("body", {}).get("items", [])
                
                # API response for single item can be a dict, not a list
                if isinstance(items, dict):
                    items = [items]
                
                if not items:
                    return None
                
                # The API returns data for E/W sub-gates within the single item
                for item in items:
                    if item.get('gate') == gate_id[-1]: # 'E' or 'W'
                        return item
                return None # Sub-gate not found
            except requests.RequestException as e:
                logger.warning(f"API fetch attempt {attempt+1} failed for {gate_id}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.backoff_factor * (2 ** attempt))
                else:
                    logger.error(f"API fetch failed for {gate_id} after {self.max_retries} retries.")
        return None


class CongestionProcessor:
    """
    Processes raw congestion data to build a cleaned, smoothed CongestionSnapshot.
    """

    def __init__(self, ewma_alpha: float = 0.4, min_required_gates: int = 6):
        self.last_snapshot: CongestionSnapshot | None = None
        self.ewma_alpha = ewma_alpha
        self.min_required_gates = min_required_gates

    def build_snapshot(
        self,
        raw_items: Dict[str, Dict[str, Any]],
        features: Dict[str, Any],
        fallback_level: int,
    ) -> CongestionSnapshot:
        """
        Constructs a CongestionSnapshot from raw data and contextual features.

        Args:
            raw_items: A dictionary of raw data from the API, keyed by gate ID.
            features: A dictionary of contextual features (weather, schedule, etc.).
            fallback_level: An integer indicating the data quality (0=realtime, >0=synthetic).

        Returns:
            A processed and validated CongestionSnapshot.
        """
        gate_wait: Dict[str, float] = {}
        gate_length: Dict[str, int] = {}
        
        for gate_id, item in raw_items.items():
            try:
                # API uses 'waitTime' and 'waitPerson', but script used 'waitLength'
                # Let's stick to the script's naming convention for consistency
                wt = float(item.get("waitTime", 0) or 0)
                wl = int(float(item.get("waitPerson", 0) or 0)) # waitPerson is the queue length
                gate_wait[gate_id] = clamp(wt, 0, 60)
                gate_length[gate_id] = int(clamp(wl, 0, 1000))
            except (ValueError, TypeError):
                continue

        # Apply winsorization to remove extreme outliers
        if gate_wait:
            waits_list = list(gate_wait.values())
            winsorized_waits = winsorize(waits_list, p=0.05)
            for i, gate_id in enumerate(gate_wait.keys()):
                gate_wait[gate_id] = winsorized_waits[i]

        quality = self._calculate_quality_score(gate_wait, gate_length)

        # Apply EWMA smoothing if a previous snapshot exists
        if self.last_snapshot and len(gate_wait) >= self.min_required_gates:
            for g, current_wait in gate_wait.items():
                if g in self.last_snapshot.gate_wait:
                    prev_wait = self.last_snapshot.gate_wait[g]
                    gate_wait[g] = self.ewma_alpha * current_wait + (1 - self.ewma_alpha) * prev_wait

        snapshot = CongestionSnapshot(
            gate_wait=gate_wait,
            gate_length=gate_length,
            source="realtime_api" if fallback_level == 0 else "synthetic",
            collected_at=datetime.now(),
            quality_score=quality,
            quality_pred_based=features.get("quality_pred_based", 0.5),
            raw_count=len(gate_wait),
            raw_items=raw_items,
            fallback_level=fallback_level,
            snapshot_id=features["snapshot_id"],
            hour_of_week=features["hour_of_week"],
            is_holiday=features.get("is_holiday"),
            schedule_density=features.get("schedule_density"),
            weather_temp=features.get("weather_temp"),
            weather_rain=features.get("weather_rain"),
        )

        self.last_snapshot = snapshot
        return snapshot

    def _calculate_quality_score(self, gate_wait: Dict[str, float], gate_length: Dict[str, int]) -> float:
        """Calculates a data quality score based on completeness, variance, and correlation."""
        n = len(gate_wait)
        if n == 0:
            return 0.0
        
        completeness = n / len(GATES_T1)

        waits = list(gate_wait.values())
        lengths = list(gate_length.values())

        # Score based on variance (prefers moderate, non-zero variance)
        w_std = np.std(waits) if waits else 0
        variance_score = 1.0 - clamp(abs(w_std - 8.0) / 20.0, 0, 1)

        # Score based on correlation between wait time and queue length
        corr = 0.0
        if len(waits) >= 3 and len(lengths) == len(waits):
            try:
                corr_matrix = np.corrcoef(waits, lengths)
                if corr_matrix.shape == (2, 2):
                    corr = corr_matrix[0, 1]
                    if np.isnan(corr):
                        corr = 0.0
            except Exception:
                corr = 0.0
        corr_score = 0.5 + 0.5 * abs(corr)

        quality = 0.5 * completeness + 0.3 * variance_score + 0.2 * corr_score
        return float(clamp(quality, 0.0, 1.0))


class RealtimeCongestionService:
    """
    Orchestrates the fetching, processing, and persistence of real-time congestion data.
    """

    def __init__(self, db_writer: DBWriter, feature_store: FeatureStore):
        self.client = RealtimeCongestionClient()
        self.processor = CongestionProcessor()
        self.db_writer = db_writer
        self.feature_store = feature_store
        self.config = get_config()

    def fetch_and_persist_snapshot(self) -> CongestionSnapshot:
        """
        The main method to get a new congestion snapshot. It handles API calls,
        data processing, fallback to synthetic data if needed, and database persistence.

        Returns:
            The latest CongestionSnapshot.
        """
        raw_items: Dict[str, Dict[str, Any]] = {}
        for gate_id in GATES_T1:
            item = self.client.fetch_gate_data(gate_id)
            if item:
                raw_items[gate_id] = item
        
        now = datetime.now()
        features = self._get_contextual_features(now)

        if len(raw_items) >= self.processor.min_required_gates:
            snapshot = self.processor.build_snapshot(raw_items, features, fallback_level=0)
        else:
            logger.warning(
                f"Fetched only {len(raw_items)} gates, which is below the minimum of "
                f"{self.processor.min_required_gates}. Generating synthetic data."
            )
            snapshot = self._generate_synthetic_snapshot(features, now)

        self._persist_snapshot_to_db(snapshot)
        return snapshot

    def _get_contextual_features(self, t: datetime) -> Dict[str, Any]:
        """Gathers supplementary features like weather and schedule density."""
        how = hour_of_week(t)
        
        is_holiday = self.feature_store.is_holiday(t)
        schedule_density = self.feature_store.get_schedule_density(how) or 120.0
        temp, rain = self.feature_store.get_weather_hourly(t)
        
        # Fallbacks for feature store misses
        temp = temp if temp is not None else 15.0
        rain = rain if rain is not None else 0.0

        # Heuristic for prediction quality based on schedule density
        quality_pred_based = clamp(0.4 + min(schedule_density / 300.0, 0.6), 0.2, 0.9)

        return {
            "snapshot_id": str(uuid.uuid4()),
            "hour_of_week": how,
            "is_holiday": is_holiday,
            "schedule_density": float(schedule_density),
            "weather_temp": float(temp),
            "weather_rain": float(rain),
            "quality_pred_based": float(quality_pred_based),
        }

    def _generate_synthetic_snapshot(self, features: Dict[str, Any], now: datetime) -> CongestionSnapshot:
        """Creates a plausible but synthetic snapshot when API data is unavailable."""
        gate_wait = {g: float(clamp(random.gauss(9, 4), 1, 25)) for g in GATES_T1}
        gate_length = {g: int(clamp(random.gauss(60, 25), 0, 300)) for g in GATES_T1}

        snapshot = CongestionSnapshot(
            gate_wait=gate_wait,
            gate_length=gate_length,
            source="synthetic",
            collected_at=now,
            quality_score=0.3, # Low but non-zero quality for synthetic data
            quality_pred_based=features["quality_pred_based"],
            raw_count=0,
            fallback_level=2, # Indicates a high level of fallback
            snapshot_id=features["snapshot_id"],
            hour_of_week=features["hour_of_week"],
            is_holiday=features["is_holiday"],
            schedule_density=features["schedule_density"],
            weather_temp=features["weather_temp"],
            weather_rain=features["weather_rain"],
        )
        self.processor.last_snapshot = snapshot
        return snapshot

    def _persist_snapshot_to_db(self, snapshot: CongestionSnapshot) -> None:
        """Converts a snapshot to a DataFrame and writes it to the `congestion_data` table."""
        rows = []
        for gate_id, wait_time in snapshot.gate_wait.items():
            rows.append({
                "terminal_id": TERMINAL_ID,
                "terminal_name": TERMINAL_NAME,
                "gate_id": gate_id,
                "wait_time": float(wait_time),
                "wait_length": int(snapshot.gate_length.get(gate_id, 0)),
                "occur_time": snapshot.collected_at,
                "hour_of_day": snapshot.collected_at.hour,
                "day_of_week": snapshot.collected_at.weekday(),
                "collected_at": snapshot.collected_at,
                "model_version": self.config["system_version"],
                "transform_version": self.config["transform_version"],
                "snapshot_id": snapshot.snapshot_id,
                "quality_pred_based": snapshot.quality_pred_based,
                "fallback_level": snapshot.fallback_level,
                "hour_of_week": snapshot.hour_of_week,
                "is_holiday": snapshot.is_holiday,
                "schedule_density": snapshot.schedule_density,
                "weather_temp": snapshot.weather_temp,
                "weather_rain": snapshot.weather_rain,
            })
        
        if rows:
            df = pd.DataFrame(rows)
            self.db_writer.insert_df("congestion_data", df)