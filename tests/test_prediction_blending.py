from src.pipeline.engine import AirportOptimizationEngine
from src.db import get_engine, FeatureStore

# This is a unit test and doesn't require a live DB connection
# We can mock the engine and feature store if needed, but for this simple test, it's okay.

def test_blend_distribution_logic():
    """
    Tests the logic of the _blend_distribution method in the main engine.
    """
    # We don't need a real engine for this unit test
    mock_engine = None
    mock_fs = None
    system = AirportOptimizationEngine(engine=mock_engine, feature_store=mock_fs)

    # Case 1: High quality real-time data, should weigh RT more
    blended1 = system._predict_and_blend_dist_internal(
        realtime_wait=10.0,
        pred_dist={"mu": 20.0, "sigma": 5.0},
        quality_rt=0.9,
        risk_score=50.0
    )
    assert 10.0 < blended1["mu"] < 15.0  # Should be closer to 10 than 20

    # Case 2: Low quality real-time data, should weigh prediction more
    blended2 = system._predict_and_blend_dist_internal(
        realtime_wait=10.0,
        pred_dist={"mu": 20.0, "sigma": 5.0},
        quality_rt=0.1,
        risk_score=50.0
    )
    assert 15.0 < blended2["mu"] < 20.0 # Should be closer to 20 than 10

    # Case 3: High risk score should inflate sigma
    blended3 = system._predict_and_blend_dist_internal(
        realtime_wait=15.0,
        pred_dist={"mu": 15.0, "sigma": 3.0},
        quality_rt=0.5,
        risk_score=80.0 # High risk
    )
    
    blended4 = system._predict_and_blend_dist_internal(
        realtime_wait=15.0,
        pred_dist={"mu": 15.0, "sigma": 3.0},
        quality_rt=0.5,
        risk_score=20.0 # Low risk
    )
    assert blended3["sigma"] > blended4["sigma"]

    # Ensure sigma has a floor
    assert blended1["sigma"] >= 1.5