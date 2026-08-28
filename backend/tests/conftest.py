"""Test-wide configuration: tier markers come from the directory, not from each test."""

from pathlib import Path

import pytest

TIERS = ("unit", "component", "integration")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test with the tier it lives in, so `-m unit` needs no hand-written marks."""
    for item in items:
        for tier in TIERS:
            if f"/tests/{tier}/" in Path(item.fspath).as_posix():
                item.add_marker(getattr(pytest.mark, tier))
