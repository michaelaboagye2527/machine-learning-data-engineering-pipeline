"""Shared test setup."""

import pytest
from prefect.testing.utilities import prefect_test_harness


@pytest.fixture(autouse=True, scope="session")
def prefect_for_tests():
    """Run every flow in the tests against a throwaway Prefect database."""
    with prefect_test_harness():
        yield
