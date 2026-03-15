"""Pytest fixtures for Swarm integration tests."""
import pytest


@pytest.fixture
def model_dirs() -> list[str]:
    """Default model directories used by pytest for integration tests."""
    return ["C:\\AI\\Models", "C:\\Users\\Public\\AI\\Models"]
