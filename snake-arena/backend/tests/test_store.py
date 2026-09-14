from __future__ import annotations

import pytest

from app.store import Store


@pytest.mark.anyio
async def test_tick_watch_does_not_advance_faster_than_the_tick_interval() -> None:
    store = Store()
    first = await store.tick_watch()
    second = await store.tick_watch()
    assert first == second


@pytest.mark.anyio
async def test_tick_watch_advances_after_the_interval_elapses() -> None:
    store = Store()
    first = await store.tick_watch()
    store._last_tick_monotonic -= 1  # simulate the tick interval having elapsed
    second = await store.tick_watch()
    assert (first.tick_count, first.snake) != (second.tick_count, second.snake) or first.status == "game-over"
