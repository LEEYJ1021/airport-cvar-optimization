import pytest
from sqlalchemy import text

from src.db import get_engine, run_migrations

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


def test_migrations_run_without_error(monkeypatch):
    """
    Tests that the migration script runs without throwing an error.
    This is a basic smoke test. It assumes a test DB is configured.
    """
    # In a real CI, you'd patch get_config to point to a test DB
    engine = get_engine(echo=False)
    
    # Run migrations
    run_migrations()

    # Verify a table exists
    with engine.connect() as conn:
        result = conn.execute(text("SHOW TABLES LIKE 'congestion_data';")).fetchone()
        assert result is not None
        assert result[0] == 'congestion_data'