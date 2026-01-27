import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from src.analytics.offline_replay import OfflineReplayAnalyzer

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@patch('src.analytics.offline_replay.get_engine')
def test_offline_replay_pipeline_graceful_failure(mock_get_engine):
    """
    Tests that the offline replay analyzer handles a missing experiment ID gracefully.
    """
    # Setup a mock engine that returns an empty DataFrame
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = []
    mock_get_engine.return_value = mock_engine

    # Use a dummy ID that won't be found
    analyzer = OfflineReplayAnalyzer(experiment_id="dummy-nonexistent-id")

    # We expect a ValueError because no data will be found
    with pytest.raises(ValueError, match="No data found for experiment_id"):
        analyzer.run_full_pipeline(output_dir="test_output")


@patch('src.analytics.offline_replay.get_engine')
@patch('pandas.read_sql')
def test_offline_replay_with_mock_data(mock_read_sql, mock_get_engine):
    """
    Tests the full analysis pipeline with a small, mocked dataset.
    """
    # Create a mock DataFrame
    mock_data = {
        'experiment_id': ['test-id'] * 4,
        'scenario': ['Q4'] * 4,
        'policy_version': ['v1-baseline', 'v1-baseline', 'v1-cvar', 'v1-cvar'],
        'realized_total': [25.0, 28.0, 20.0, 22.0],
        'missed': [0, 1, 0, 0],
        'accepted': [1, 0, 1, 1],
        'ts': pd.to_datetime(['2026-01-01 10:00', '2026-01-01 10:05', '2026-01-01 10:00', '2026-01-01 10:05']),
        'recommended_gate': ['DG1_W', 'DG1_E', 'DG2_W', 'DG2_W'],
    }
    mock_read_sql.return_value = pd.DataFrame(mock_data)
    
    analyzer = OfflineReplayAnalyzer(experiment_id="test-id")
    
    # Mock the export and visualization parts to avoid creating files
    with patch('src.analytics.tables.TableExporter.export_all') as mock_export, \
         patch('src.analytics.visualization.FigureGenerator._save_plot') as mock_save_plot:
        
        analyzer.run_full_pipeline(output_dir="test_output")

        # Check that the main results were computed
        assert "q4_metrics" in analyzer.results
        assert not analyzer.results["q4_metrics"].empty
        assert "e1_e5_tests" in analyzer.results
        
        # Check a specific computed value
        baseline_apt = analyzer.results["q4_metrics"][analyzer.results["q4_metrics"]["policy_group"] == "baseline"]["APT_mean"].iloc[0]
        assert baseline_apt == pytest.approx(26.5)

        # Check that export was called
        mock_export.assert_called_once()