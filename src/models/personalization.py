from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PassengerProfile:
    """Represents the characteristics of a passenger."""
    age_group: str | None = None      # 'child', 'adult', 'senior'
    mobility: str | None = None       # 'normal', 'low'
    bags: int | None = None           # Number of checked bags
    companions: int | None = None     # Number of companions
    airline_checkin_counter: str | None = None


class BayesianImputer:
    """
    Imputes missing passenger profile attributes using prior distributions.
    This allows the system to work even with incomplete user input.
    """
    age_prior: Dict[str, float] = {"child": 0.05, "adult": 0.75, "senior": 0.20}
    mobility_prior: Dict[str, float] = {"normal": 0.85, "low": 0.15}
    bags_prior_mean: float = 1.2
    bags_prior_std: float = 0.9
    companions_prior_mean: float = 0.6
    companions_prior_std: float = 0.95

    def impute(self, profile: PassengerProfile) -> PassengerProfile:
        """
        Fills in any missing attributes of a PassengerProfile in-place.

        Args:
            profile: The passenger profile, which may have None values.

        Returns:
            The same profile instance with missing values imputed.
        """
        if profile.age_group is None:
            profile.age_group = self._sample_categorical(self.age_prior)
        if profile.mobility is None:
            profile.mobility = self._sample_categorical(self.mobility_prior)
        if profile.bags is None:
            profile.bags = max(0, int(round(random.gauss(self.bags_prior_mean, self.bags_prior_std))))
        if profile.companions is None:
            profile.companions = max(0, int(round(random.gauss(self.companions_prior_mean, self.companions_prior_std))))
        return profile

    def _sample_categorical(self, probs: Dict[str, float]) -> str:
        """Samples a category from a dictionary of probabilities."""
        r = random.random()
        cumulative = 0.0
        for category, prob in probs.items():
            cumulative += prob
            if r <= cumulative:
                return category
        return list(probs.keys())[-1]  # Fallback for floating point inaccuracies


@dataclass
class WalkingTimeModel:
    """
    Models passenger walking time by applying adjustment factors to a base time.
    """
    def get_speed_factor(self, profile: PassengerProfile) -> float:
        """
        Calculates a speed adjustment factor based on the passenger profile.
        A factor > 1.0 means the passenger is slower than average.

        Args:
            profile: The passenger's profile.

        Returns:
            A speed adjustment factor.
        """
        factor = 1.0
        if profile.age_group == "child":
            factor *= 1.10
        elif profile.age_group == "senior":
            factor *= 1.30
        
        if profile.mobility == "low":
            factor *= 1.35
        
        if profile.bags is not None:
            factor *= (1.0 + 0.05 * min(profile.bags, 4))
        
        if profile.companions is not None:
            factor *= (1.0 + 0.03 * min(profile.companions, 4))
            
        return factor

    def adjust_time(self, base_minutes: float, profile: PassengerProfile) -> float:
        """
        Adjusts a base walking time using the calculated speed factor.

        Args:
            base_minutes: The standard walking time in minutes.
            profile: The passenger's profile.

        Returns:
            The adjusted walking time in minutes.
        """
        return base_minutes * self.get_speed_factor(profile)


@dataclass
class CheckinQueueModel:
    """
    Estimates the time a passenger will spend in a check-in queue.
    """
    # Using Gamma distribution priors for check-in time: E[T] = alpha/beta
    alpha_prior: float = 3.0
    beta_prior: float = 0.3  # Implies a mean of 10 minutes

    def estimate_time(
        self,
        profile: PassengerProfile,
        time_context: str,
        observed_wait: Optional[float] = None
    ) -> float:
        """
        Estimates check-in queue time based on profile and time of day.

        Args:
            profile: The passenger's profile.
            time_context: A string representing the time of day (e.g., 'morning_peak').
            observed_wait: If an actual wait time is observed, it overrides the model.

        Returns:
            The estimated check-in time in minutes.
        """
        if observed_wait is not None:
            return max(1.0, observed_wait)

        base_mean = self.alpha_prior / self.beta_prior

        time_multiplier = {
            "early": 0.9,
            "morning_peak": 1.3,
            "midday": 1.0,
            "afternoon_peak": 1.2,
            "evening": 1.1,
            "night": 0.8
        }.get(time_context, 1.0)

        complexity_factor = 1.0
        if profile.bags is not None:
            complexity_factor *= 1.0 + 0.08 * min(profile.bags, 4)
        if profile.companions is not None:
            complexity_factor *= 1.0 + 0.05 * min(profile.companions, 4)
        if profile.age_group == "senior":
            complexity_factor *= 1.10
        if profile.mobility == "low":
            complexity_factor *= 1.15

        return base_mean * time_multiplier * complexity_factor