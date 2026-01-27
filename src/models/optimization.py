from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import numpy as np

from src.models.personalization import CheckinQueueModel, PassengerProfile, WalkingTimeModel
from src.utils.helpers import is_gate_open, minutes_between

logger = logging.getLogger("airport.models.optimization")


class OptimizationAgent:
    """
    The core agent responsible for scoring routes based on a tail-risk objective.
    """

    def __init__(self):
        self.walk_model = WalkingTimeModel()
        self.checkin_model = CheckinQueueModel()

    def score_route(
        self,
        travel_to_checkin: float,
        checkin_time: float,
        checkin_to_gate: float,
        gate_wait_dist: Dict[str, float],
        profile: PassengerProfile,
        gate_id: str,
        now_time: datetime,
        objective: str = "cvar",
        cvar_alpha: float = 0.9,
        quantile_tau: float = 0.9,
        miss_penalty_factor: float = 2.0,
        required_gate_time: Optional[datetime] = None,
        last_recommended_gate: Optional[str] = None,
        hysteresis_penalty: float = 1.5,
        risk_score: Optional[float] = None,
        enforce_gate_hours: bool = True,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculates a risk score for a complete passenger route.

        Args:
            travel_to_checkin: Time from arrival point to check-in.
            checkin_time: Estimated time in check-in queue.
            checkin_to_gate: Time from check-in to security gate.
            gate_wait_dist: Predicted distribution of security gate wait time.
            profile: The passenger's profile.
            gate_id: The target security gate.
            now_time: The current time.
            objective: The risk metric to use ('cvar', 'quantile', 'mean').
            cvar_alpha: The alpha level for CVaR (e.g., 0.9 for the worst 10% of outcomes).
            miss_penalty_factor: Multiplier for time past the required arrival.
            required_gate_time: The latest time the passenger must be at the gate.
            last_recommended_gate: The previously recommended gate for this user.
            hysteresis_penalty: Penalty for switching from the last recommendation.
            risk_score: A pre-computed risk score for the gate's congestion.
            enforce_gate_hours: Whether to apply a large penalty for closed gates.

        Returns:
            A tuple containing the final route score and a dictionary of its components.
        """
        # Personalize travel times
        adj_to_checkin = self.walk_model.adjust_time(travel_to_checkin, profile)
        adj_to_gate = self.walk_model.adjust_time(checkin_to_gate, profile)

        # Simulate total time distribution
        mu, sigma = gate_wait_dist["mu"], gate_wait_dist["sigma"]
        samples = np.random.normal(mu, sigma, size=500)
        base_time = adj_to_checkin + checkin_time + adj_to_gate
        total_time_samples = np.maximum(0.1, base_time + samples)

        # Calculate the core risk metric based on the chosen objective
        if objective == "mean":
            risk_metric = float(np.mean(total_time_samples))
        elif objective == "quantile":
            risk_metric = float(np.quantile(total_time_samples, quantile_tau))
        else:  # 'cvar'
            q = np.quantile(total_time_samples, cvar_alpha)
            tail_samples = total_time_samples[total_time_samples >= q]
            risk_metric = float(np.mean(tail_samples)) if len(tail_samples) > 0 else float(q)

        # --- Calculate Penalties ---
        gate_arrival_time = now_time + timedelta(minutes=base_time)
        
        gate_closed_penalty = 0.0
        if enforce_gate_hours and not is_gate_open(gate_id, gate_arrival_time):
            gate_closed_penalty = 9999.0

        miss_penalty = 0.0
        if required_gate_time and gate_arrival_time > required_gate_time:
            missed_minutes = minutes_between(required_gate_time, gate_arrival_time)
            miss_penalty = miss_penalty_factor * missed_minutes

        hysteresis = 0.0
        if last_recommended_gate and last_recommended_gate != gate_id:
            hysteresis = hysteresis_penalty

        # Add a small penalty based on the pre-computed feature-based risk score
        risk_penalty = 0.05 * (risk_score or 0.0)

        # Final score is the risk metric plus all penalties
        final_score = risk_metric + gate_closed_penalty + miss_penalty + hysteresis + risk_penalty

        components = {
            "base_time": base_time,
            "risk_metric": risk_metric,
            "gate_closed_penalty": gate_closed_penalty,
            "miss_penalty": miss_penalty,
            "hysteresis": hysteresis,
            "risk_penalty": risk_penalty,
            "final_score": final_score,
        }
        return final_score, components


class ExplanationAgent:
    """
    Generates human-readable explanations for the recommendations.
    """

    def summarize(self, recommendation: Dict[str, Any]) -> str:
        """
        Creates a summary of why a particular gate was recommended.

        Args:
            recommendation: The dictionary of the winning route.

        Returns:
            A human-readable explanation string.
        """
        if not recommendation:
            return "No recommendation available at this time."

        gate_id = recommendation.get("gate_id", "N/A")
        return (
            f"The recommended gate ({gate_id}) was selected by minimizing tail-risk (CVaR). "
            f"The decision considers a blend of real-time data and predictive forecasts, "
            f"personalized travel times, gate operating hours, and overall congestion risk."
        )