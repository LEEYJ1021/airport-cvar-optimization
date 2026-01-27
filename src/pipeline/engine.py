from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.db.engine import DBWriter
from src.db.feature_store import FeatureStore
from src.ingest.external import ExternalDataIngestor
from src.ingest.realtime import CongestionSnapshot, RealtimeCongestionService
from src.models.optimization import ExplanationAgent, OptimizationAgent
from src.models.personalization import BayesianImputer, PassengerProfile
from src.models.predictors import (
    KalmanPredictor,
    MarkovPredictorAdapter,
    PredictorStrategy,
    QuantileHeuristicPredictor,
)
from src.settings import (
    CHECKIN_COUNTERS,
    CHECKIN_TO_GATE,
    GATE_OPERATING_HOURS,
    GATES_T1,
    get_config,
)
from src.utils.helpers import get_travel_time, hour_to_slot, is_gate_open, sigmoid

logger = logging.getLogger("airport.pipeline.engine")


class T1FeatureBuilder:
    """
    Builds advanced features by fusing real-time snapshots with passenger and weather data.
    """

    def __init__(self, db_writer: DBWriter):
        self.db_writer = db_writer
        self.config = get_config()
        self.gate_capacity_config = {
            "DG1": 500, "DG2": 500, "DG3": 800, "DG4": 800, "DG5": 300, "DG6": 300
        }
        self.risk_weights = {
            "wait_time": 0.25, "wait_length": 0.20, "load_to_capacity": 0.30,
            "schedule_density": 0.15, "weather_rain": 0.10,
        }

    def build_features(
        self,
        snapshot: CongestionSnapshot,
        df_pass_t1: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Creates a feature DataFrame for a given snapshot.

        Args:
            snapshot: The real-time congestion snapshot.
            df_pass_t1: DataFrame with passenger forecast data for T1.

        Returns:
            A DataFrame of rich features for each gate.
        """
        time_slot = hour_to_slot(snapshot.collected_at.hour)
        date_str = snapshot.collected_at.strftime("%Y%m%d")

        # Get passenger load for the current time slot
        df_slot = df_pass_t1[df_pass_t1["time_slot"] == time_slot] if not df_pass_t1.empty else pd.DataFrame()
        load_by_dg = {f"DG{i}": 0.0 for i in range(1, 7)}
        if not df_slot.empty:
            for _, r in df_slot.iterrows():
                load_by_dg[r["departure_gate"]] = float(r.get("expected_passenger_load", 0.0))

        # Distribute load from main departure areas (DG1-6) to sub-gates (DG1_W, DG1_E)
        split_map = self._split_load_by_subgate(snapshot, load_by_dg)

        rows = []
        for gate_id in GATES_T1:
            base_gate = gate_id.split("_")[0]
            capacity = self.gate_capacity_config.get(base_gate, 500) / 2.0  # Assume E/W split capacity
            expected_load = split_map.get(gate_id, 0.0)
            
            wait_time = snapshot.gate_wait.get(gate_id, 8.0)
            wait_length = snapshot.gate_length.get(gate_id, 0)
            
            load_to_capacity = expected_load / capacity if capacity > 0 else 0.0
            queue_pressure = wait_time * math.log(wait_length + 1) if wait_length > 0 else 0.0
            
            risk_score = self._calculate_risk_score(
                wait_time, wait_length, load_to_capacity,
                snapshot.schedule_density or 0.5, 1 if (snapshot.weather_rain or 0) > 0 else 0
            )

            rows.append({
                "snapshot_id": snapshot.snapshot_id,
                "gate_id": gate_id,
                "date": date_str,
                "time_slot": time_slot,
                "expected_passenger_load": expected_load,
                "gate_processing_capacity": capacity,
                "load_to_capacity_ratio": load_to_capacity,
                "queue_pressure_index": queue_pressure,
                "congestion_state": self._classify_congestion(wait_time, wait_length),
                "data_reliability_score": snapshot.quality_pred_based * (1 - snapshot.fallback_level),
                "is_prediction_only": 1 if wait_length == 0 and snapshot.quality_pred_based < 0.7 else 0,
                "congestion_risk_score": risk_score,
                "schedule_density": snapshot.schedule_density,
                "weather_temp": snapshot.weather_temp,
                "weather_rain_flag": 1 if (snapshot.weather_rain or 0) > 0 else 0,
                "weather_rain_mm": snapshot.weather_rain,
                "model_version": self.config["system_version"],
                "transform_version": self.config["transform_version"],
                "collected_at": snapshot.collected_at,
            })

        df_feat = pd.DataFrame(rows)
        self.db_writer.insert_df("congestion_features_t1", df_feat)
        return df_feat

    def _split_load_by_subgate(self, snapshot: CongestionSnapshot, load_by_dg: Dict[str, float]) -> Dict[str, float]:
        """Splits passenger load between East/West sub-gates based on queue length ratio."""
        out = {}
        for i in range(1, 7):
            dg, load = f"DG{i}", load_by_dg.get(f"DG{i}", 0.0)
            g_w, g_e = f"{dg}_W", f"{dg}_E"
            lw, le = snapshot.gate_length.get(g_w, 0), snapshot.gate_length.get(g_e, 0)
            total_len = lw + le
            w_ratio = lw / total_len if total_len > 0 else 0.5
            out[g_w] = load * w_ratio
            out[g_e] = load * (1 - w_ratio)
        return out

    def _classify_congestion(self, wait_time: float, wait_length: int) -> str:
        if wait_time < 10 and wait_length < 20: return "SMOOTH"
        if wait_time < 20: return "NORMAL"
        if wait_time < 30: return "BUSY"
        return "CONGESTED"

    def _calculate_risk_score(self, wait_time, wait_length, load_to_capacity, schedule_density, rain_flag) -> float:
        """Calculates a weighted, normalized risk score from multiple features."""
        norm_wait_time = min(wait_time / 60.0, 1.0)
        norm_wait_length = min(wait_length / 300.0, 1.0)
        norm_load = min(load_to_capacity / 2.0, 1.0)
        norm_schedule = min(schedule_density, 1.0)

        score = (
            self.risk_weights["wait_time"] * norm_wait_time +
            self.risk_weights["wait_length"] * norm_wait_length +
            self.risk_weights["load_to_capacity"] * norm_load +
            self.risk_weights["schedule_density"] * norm_schedule +
            self.risk_weights["weather_rain"] * rain_flag
        )
        return float(score * 100)


class AirportOptimizationEngine:
    """
    The main orchestration engine for the airport optimization system.
    It integrates all components to provide route recommendations.
    """

    def __init__(self, engine, feature_store: FeatureStore):
        self.db_writer = DBWriter(engine)
        self.feature_store = feature_store
        
        self.perception = RealtimeCongestionService(self.db_writer, self.feature_store)
        self.external = ExternalDataIngestor(self.db_writer)
        self.feature_builder = T1FeatureBuilder(self.db_writer)
        
        self.predictors: List[PredictorStrategy] = [
            MarkovPredictorAdapter(), KalmanPredictor(), QuantileHeuristicPredictor()
        ]
        self.optimizer = OptimizationAgent()
        self.imputer = BayesianImputer()
        self.explainer = ExplanationAgent()
        
        self.last_recommended_gate: Optional[str] = None
        self.last_passenger_t1: Optional[pd.DataFrame] = None

    def _prepare_data(self) -> Tuple[CongestionSnapshot, pd.DataFrame]:
        """Ensures all necessary real-time and external data is fresh."""
        if self.last_passenger_t1 is None:
            self.external.fetch_and_process_metar()
            self.last_passenger_t1 = self.external.fetch_and_process_passenger_forecast()
        
        snapshot = self.perception.fetch_and_persist_snapshot()
        df_feat = self.feature_builder.build_features(
            snapshot, self.last_passenger_t1 if self.last_passenger_t1 is not None else pd.DataFrame()
        )
        return snapshot, df_feat

    def _get_time_context(self, t: datetime) -> str:
        h = t.hour
        if 0 <= h < 6: return "night"
        if 6 <= h < 9: return "early"
        if 9 <= h < 12: return "morning_peak"
        if 12 <= h < 15: return "midday"
        if 15 <= h < 18: return "afternoon_peak"
        return "evening"

    def _predict_and_blend_dist(
        self, gate_id: str, snapshot: CongestionSnapshot, df_feat: pd.DataFrame
    ) -> Dict[str, float]:
        """Generates an ensemble prediction and blends it with real-time data."""
        time_context = self._get_time_context(snapshot.collected_at)
        feat_row = df_feat[df_feat['gate_id'] == gate_id].iloc[0] if not df_feat[df_feat['gate_id'] == gate_id].empty else {}
        
        # Ensemble prediction
        dists = [
            pred.predict_distribution(gate_id, {**snapshot.__dict__, **feat_row})
            for pred in self.predictors
        ]
        pred_mu = float(np.mean([d["mu"] for d in dists]))
        pred_sigma = float(np.mean([d["sigma"] for d in dists]))

        # Blend with real-time observation
        real_wait = snapshot.gate_wait.get(gate_id, pred_mu)
        w_rt = sigmoid(6.0 * (snapshot.quality_score - 0.5))
        w_pred = 1.0 - w_rt
        
        mu = w_rt * real_wait + w_pred * pred_mu
        sigma = w_rt * (0.1 * real_wait) + w_pred * pred_sigma
        
        # Inflate variance based on risk score
        risk_score = feat_row.get("congestion_risk_score", 0.0)
        if risk_score > 60:
            sigma *= 1.15

        return {"mu": mu, "sigma": max(1.5, sigma)}

    def recommend_route(
        self,
        profile: PassengerProfile,
        origin_type: str,
        origin_location: str,
        required_gate_time: Optional[datetime],
        allowed_counters: Optional[List[str]] = None,
        parking_occupancy: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Generic recommendation function for all scenarios (Q1-Q4)."""
        snapshot, df_feat = self._prepare_data()
        profile = self.imputer.impute(profile)
        time_context = self._get_time_context(snapshot.collected_at)
        now = snapshot.collected_at

        allowed_counters = allowed_counters or CHECKIN_COUNTERS
        
        candidates = []
        for counter in allowed_counters:
            travel_to_checkin = get_travel_time(origin_type, origin_location, counter)
            if origin_type == "parking":
                occupancy = parking_occupancy or random.uniform(0.6, 0.95)
                travel_to_checkin += 2 + 10 * (occupancy ** 2)

            checkin_time = self.optimizer.checkin_model.estimate_time(profile, time_context)

            for gate_id in GATES_T1:
                if not is_gate_open(gate_id, now):
                    continue

                checkin_to_gate = CHECKIN_TO_GATE.get(gate_id, 10.0)
                dist = self._predict_and_blend_dist(gate_id, snapshot, df_feat)
                feat_row = df_feat[df_feat['gate_id'] == gate_id].iloc[0] if not df_feat[df_feat['gate_id'] == gate_id].empty else {}
                
                score, comps = self.optimizer.score_route(
                    travel_to_checkin, checkin_time, checkin_to_gate, dist, profile, gate_id, now,
                    required_gate_time=required_gate_time,
                    last_recommended_gate=self.last_recommended_gate,
                    risk_score=feat_row.get("congestion_risk_score")
                )

                candidates.append({
                    "origin": origin_location,
                    "checkin_counter": counter,
                    "gate_id": gate_id,
                    "score": score,
                    "components": comps,
                    "gate_wait_dist": dist,
                    "gate_operating_hours": GATE_OPERATING_HOURS.get(gate_id, "N/A"),
                })
        
        candidates.sort(key=lambda x: x["score"])
        top3 = candidates[:3]
        if top3:
            self.last_recommended_gate = top3[0]["gate_id"]

        return {
            "top3_routes": top3,
            "data_source": snapshot.source,
            "quality_score": snapshot.quality_score,
            "collected_at": snapshot.collected_at.isoformat(),
            "explanation": self.explainer.summarize(top3[0] if top3 else {})
        }