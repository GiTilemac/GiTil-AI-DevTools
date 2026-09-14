"""Tests for the SQLAlchemy-backed store itself (persistence, isolation,
uniqueness) - as opposed to tests/test_auth.py and test_leaderboard.py,
which exercise the same store indirectly through the HTTP API.
"""

from __future__ import annotations

import pytest

from app.models import GameMode
from app.store import Store, UsernameTakenError


def test_file_backed_store_persists_across_instances(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path}"

    first = Store(database_url=url)
    first.create_user("persisted", "hash")

    second = Store(database_url=url)
    record = second.find_user_by_username("persisted")

    assert record is not None
    assert record.username == "persisted"


def test_in_memory_stores_are_isolated_from_each_other() -> None:
    a = Store(database_url="sqlite://")
    b = Store(database_url="sqlite://")

    a.create_user("only-in-a", "hash")

    assert a.find_user_by_username("only-in-a") is not None
    assert b.find_user_by_username("only-in-a") is None


def test_create_user_raises_on_a_duplicate_username_at_the_db_level() -> None:
    s = Store(database_url="sqlite://")
    s.create_user("dupe", "hash1")

    with pytest.raises(UsernameTakenError):
        s.create_user("dupe", "hash2")


def test_fresh_database_is_seeded_with_the_demo_leaderboard() -> None:
    s = Store(database_url="sqlite://")
    entries = s.get_leaderboard()
    assert len(entries) == 7


def test_reset_clears_data_and_reseeds() -> None:
    s = Store(database_url="sqlite://")
    s.create_user("temp", "hash")
    s.submit_score("temp", 999999, GameMode.WALLS)

    s.reset()

    assert s.find_user_by_username("temp") is None
    entries = s.get_leaderboard()
    assert len(entries) == 7
    assert all(e.score != 999999 for e in entries)
