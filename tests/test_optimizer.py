from datetime import datetime, timedelta

from src.models.optimization import OptimizationAgent
from src.models.personalization import PassengerProfile


def test_optimizer_scores_route():
    """Tests the basic scoring functionality of the OptimizationAgent."""
    agent = OptimizationAgent()
    profile = PassengerProfile(age_group="adult", mobility="normal", bags=1, companions=0)
    dist = {"mu": 10.0, "sigma": 3.0}
    now = datetime.now()

    score, comps = agent.score_route(
        travel_to_checkin=5.0,
        checkin_time=8.0,
        checkin_to_gate=6.0,
        gate_wait_dist=dist,
        profile=profile,
        gate_id="DG3_W",
        now_time=now,
        required_gate_time=now + timedelta(minutes=40),
    )
    assert score > 0
    assert "risk_metric" in comps
    assert comps["final_score"] == score
    assert comps["miss_penalty"] == 0 # Should not miss the flight

def test_optimizer_missed_flight_penalty():
    """Tests that a penalty is applied for missing the required gate time."""
    agent = OptimizationAgent()
    profile = PassengerProfile(age_group="adult", mobility="normal", bags=1, companions=0)
    dist = {"mu": 25.0, "sigma": 5.0} # Long wait time
    now = datetime.now()

    # Base time = 5 (walk) + 8 (checkin) + 6 (walk) = 19 min
    # Gate arrival time is ~19 min from now. Required time is 20 min from now.
    # This is very tight and likely to incur a penalty.
    score, comps = agent.score_route(
        travel_to_checkin=5.0,
        checkin_time=8.0,
        checkin_to_gate=6.0,
        gate_wait_dist=dist,
        profile=profile,
        gate_id="DG3_W",
        now_time=now,
        required_gate_time=now + timedelta(minutes=20),
    )
    # The base time is 19 mins, so arrival is at now+19. Required is now+20.
    # The check is on base time arrival, not total time.
    # Let's adjust to make it clearly miss.
    score_miss, comps_miss = agent.score_route(
        travel_to_checkin=5.0,
        checkin_time=10.0,
        checkin_to_gate=6.0,
        gate_wait_dist=dist,
        profile=profile,
        gate_id="DG3_W",
        now_time=now,
        required_gate_time=now + timedelta(minutes=20), # Base time is 21 min
    )
    assert comps_miss["miss_penalty"] > 0