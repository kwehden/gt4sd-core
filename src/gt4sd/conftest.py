"""Make pytest fixtures available to multiple test directories."""

import pytest


@pytest.fixture
def mock_wrong_s3_env(monkeypatch):
    """Changes an environment variable to break the s3 connection."""
    monkeypatch.setenv("GT4SD_S3_SECRET_KEY", "(╯°□°）╯︵ ┻━┻")


@pytest.fixture
def mock_missing_s3_env(monkeypatch):
    """Deletes an environment variable to break the s3 connection."""
    monkeypatch.delenv("GT4SD_S3_SECRET_KEY")
