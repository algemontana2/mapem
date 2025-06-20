"""Database snapshot tests.

These tests require a pre-populated database snapshot and will be skipped
unless the environment variable ``RUN_DB_SNAPSHOTS`` is set to ``1``.
"""

import os
import pytest
from sqlalchemy import text
import backend.db as db

# ── Skip all tests in this module unless enabled ──
if os.environ.get("RUN_DB_SNAPSHOTS") != "1":
    pytest.skip(
        "Skipping DB snapshot tests; set RUN_DB_SNAPSHOTS=1 to run",
        allow_module_level=True,
    )


@pytest.mark.db
def test_event_type_distribution_snapshot(latest_tree_version_id):
    """Snapshot check of event_type counts for Tree ID."""
    session = db.SessionLocal()
    try:
        result = session.execute(
            text("""
                SELECT event_type, COUNT(*)
                FROM events
                WHERE tree_id = :tree_id
                GROUP BY event_type
                ORDER BY event_type
            """),
            {"tree_id": latest_tree_version_id}
        )
        counts = dict(result.all())

        expected = {
            "birth": 99,
            "death": 74,
            "marriage": 29,
            "burial": 9,
            "residence": 10,
        }

        for event_type, expected_count in expected.items():
            actual_count = counts.get(event_type)
            assert actual_count == expected_count, (
                f"{event_type} count mismatch: expected {expected_count}, got {actual_count}"
            )

    finally:
        session.close()


@pytest.mark.db
def test_total_event_count_matches_expected(latest_tree_version_id):
    """Verify total number of events for the tree matches upload summary."""
    session = db.SessionLocal()
    try:
        result = session.execute(
            text("SELECT COUNT(*) FROM events WHERE tree_id = :tree_id"),
            {"tree_id": latest_tree_version_id}
        )
        total = result.scalar()
        assert total == 221, f"Expected 221 events, got {total}"

    finally:
        session.close()


@pytest.mark.db
def test_event_types_are_valid(latest_tree_version_id):
    """Ensure all event types used are from known list."""
    session = db.SessionLocal()
    try:
        result = session.execute(
            text("SELECT DISTINCT event_type FROM events WHERE tree_id = :tree_id"),
            {"tree_id": latest_tree_version_id}
        )
        found = {row[0] for row in result.fetchall()}
        allowed = {"birth", "death", "marriage", "residence", "burial", "census", "christening"}

        assert found.issubset(allowed), f"Invalid event types detected: {found - allowed}"

    finally:
        session.close()
