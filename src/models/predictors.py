from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Protocol

from src.settings import GATES_T1
from src.utils.helpers import clamp


class PredictorStrategy(Protocol):
    """
    A protocol defining the interface for all wait time prediction models.
    Each predictor must be able to return a full probability distribution.
    """
    name: str

    def predict_distribution(self, gate_id: str, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Predicts the wait time distribution for a given gate.

        Args:
            gate_id: The ID of the gate.
            context: A dictionary of contextual information (e.g., current wait, schedule).

        Returns:
            A dictionary representing the distribution (e.g., {'mu', 'sigma', 'q90'}).
        """
        ...


@dataclass
class MarkovCongestionPredictor:
    """
    A simple Markov Chain model to predict the next congestion state.
    """
    states: list[str] = field(default_factory=lambda: ["low", "medium", "high", "very_high"])
    transition_matrix: Dict[str, list[float]] = field(default_factory=lambda: {
        "low":       [0.60, 0.30, 0.08, 0.02],
        "medium":    [0.20, 0.55, 0.20, 0.05],
        "high":      [0.10, 0.30, 0.45, 0.15],
        "very_high": [0.05, 0.20, 0.35, 0.40]
    })
    state_wait_times: Dict[str, float] = field(default_factory=lambda: {
        "low": 3.0, "medium": 7.0, "high": 12.0, "very_high": 18.0
    })

    def _get_state_from_wait(self, wait_time: float) -> str:
        if wait_time >= 15: return "very_high"
        if wait_time >= 10: return "high"
        if wait_time >= 5:  return "medium"
        return "low"

    def predict(self, current_wait: float | None, time_context: str, steps: int = 1) -> float:
        """Predicts the wait time after a number of steps."""
        if current_wait is not None:
            state = self._get_state_from_wait(current_wait)
        else:
            # If no observation, use a prior based on time of day
            state = {
                "early": "low", "morning_peak": "high", "midday": "medium",
                "afternoon_peak": "high", "evening": "medium", "night": "low"
            }.get(time_context, "medium")

        for _ in range(steps):
            probs = self.transition_matrix[state]
            state = random.choices(self.states, probs, k=1)[0]
        
        return self.state_wait_times[state]


class MarkovPredictorAdapter:
    """An adapter to make the Markov model conform to the PredictorStrategy protocol."""
    name: str = "markov_adapter"

    def __init__(self):
        self.mc = MarkovCongestionPredictor()

    def predict_distribution(self, gate_id: str, context: Dict[str, Any]) -> Dict[str, float]:
        mu = self.mc.predict(
            current_wait=context.get("current_wait"),
            time_context=context.get("time_context", "midday")
        )
        sigma = max(2.0, 0.3 * mu)  # Heuristic for variance
        return {
            "mu": mu,
            "sigma": sigma,
            "q10": max(0.1, mu - 1.28 * sigma),
            "q50": mu,
            "q90": mu + 1.28 * sigma,
        }


class KalmanPredictor:
    """A simple Kalman Filter to predict wait times, smoothing observations over time."""
    name: str = "kalman_filter"

    def __init__(self, process_variance: float = 1.5, observation_variance: float = 4.0):
        # State (x): estimated wait time
        self.state: Dict[str, float] = {g: 8.0 for g in GATES_T1}
        # State variance (P): uncertainty in the estimate
        self.variance: Dict[str, float] = {g: 4.0 for g in GATES_T1}
        # Process variance (Q): how much we expect the state to change between steps
        self.process_variance = process_variance
        # Observation variance (R): uncertainty in the measurement
        self.observation_variance = observation_variance

    def _update(self, gate_id: str, observation: float):
        # Predict step
        x_prior = self.state[gate_id]
        p_prior = self.variance[gate_id] + self.process_variance

        # Update step
        kalman_gain = p_prior / (p_prior + self.observation_variance)
        x_post = x_prior + kalman_gain * (observation - x_prior)
        p_post = (1 - kalman_gain) * p_prior

        self.state[gate_id] = x_post
        self.variance[gate_id] = p_post

    def predict_distribution(self, gate_id: str, context: Dict[str, Any]) -> Dict[str, float]:
        observation = context.get("current_wait")
        if observation is not None:
            self._update(gate_id, observation)

        # Predict the next state's distribution
        mu = self.state[gate_id]
        sigma = max(1.5, math.sqrt(self.variance[gate_id] + self.process_variance))
        
        return {
            "mu": mu,
            "sigma": sigma,
            "q10": max(0.1, mu - 1.28 * sigma),
            "q50": mu,
            "q90": mu + 1.28 * sigma,
        }


class QuantileHeuristicPredictor:
    """
    A heuristic model that adjusts a base wait time using contextual features.
    """
    name: str = "quantile_heuristic"

    def predict_distribution(self, gate_id: str, context: Dict[str, Any]) -> Dict[str, float]:
        base_wait = context.get("current_wait", 8.0)
        
        # Contextual features
        density = context.get("schedule_density", 120.0)
        is_holiday = context.get("is_holiday", 0)
        temp = context.get("weather_temp")
        rain = context.get("weather_rain")
        load_ratio = context.get("load_to_capacity_ratio", 0.7)

        # Apply adjustments
        adj = 1.0 + 0.001 * (density - 120)
        if is_holiday:
            adj *= 1.08
        if rain is not None and rain > 0:
            adj *= 1.05
        if temp is not None and temp < 0:
            adj *= 1.03
        
        # Adjust for demand pressure
        adj *= (1.0 + 0.15 * max(0.0, load_ratio - 1.0))

        mu = clamp(base_wait * adj, 1.0, 30.0)
        sigma = clamp(0.25 * mu + 1.5, 2.0, 10.0)

        return {
            "mu": mu,
            "sigma": sigma,
            "q10": max(0.1, mu - 1.28 * sigma),
            "q50": mu,
            "q90": mu + 1.28 * sigma,
        }