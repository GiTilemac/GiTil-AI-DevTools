"""Tests for the /watch/live SSE feed.

httpx's ASGITransport (which backs both `TestClient` and `AsyncClient`)
fully drains the ASGI app coroutine before it hands back *any* response,
even for a streaming one — see `ASGITransport.handle_async_request` in
httpx's source, which does `await self.app(scope, receive, send)` before
building a `Response`. That makes a genuinely infinite stream (this
endpoint never ends on its own; a real client ends it by disconnecting)
impossible to read incrementally through the HTTP layer in tests: the
request would simply hang forever waiting for the app to return.

So this drives the endpoint's async generator directly instead of going
through an HTTP client — the generator (`_event_stream`) is the same code
that runs in production; only the outer ASGI/StreamingResponse plumbing
(pure framework boilerplate) is left untested here.
"""

from __future__ import annotations

import json

import pytest

from app.routers.watch import _event_stream


class _NeverDisconnected:
    async def is_disconnected(self) -> bool:
        return False


def _parse_sse(raw: str) -> dict:
    assert raw.startswith("data: ") and raw.endswith("\n\n")
    return json.loads(raw[len("data: "): -len("\n\n")])


@pytest.mark.anyio
async def test_watch_live_yields_current_state_immediately() -> None:
    gen = _event_stream(_NeverDisconnected())
    try:
        state = _parse_sse(await gen.__anext__())
    finally:
        await gen.aclose()

    assert state["board"] == {"width": 20, "height": 20}
    assert state["mode"] == "pass-through"
    assert state["status"] in ("running", "game-over")
    assert len(state["snake"]) >= 1


@pytest.mark.anyio
async def test_watch_live_ticks_forward() -> None:
    gen = _event_stream(_NeverDisconnected())
    try:
        first = _parse_sse(await gen.__anext__())
        second = _parse_sse(await gen.__anext__())
    finally:
        await gen.aclose()

    # The bot always advances (or restarts) between ticks, so consecutive
    # snapshots must differ somehow - either the tick count moved, or the
    # game ended and a fresh one started.
    assert (first["tickCount"], first["snake"]) != (second["tickCount"], second["snake"])


@pytest.mark.anyio
async def test_watch_live_stops_cleanly_when_the_client_disconnects() -> None:
    class _DisconnectsAfterFirstCheck:
        def __init__(self) -> None:
            self.calls = 0

        async def is_disconnected(self) -> bool:
            self.calls += 1
            return self.calls > 1

    request = _DisconnectsAfterFirstCheck()
    gen = _event_stream(request)

    await gen.__anext__()  # first tick: is_disconnected() -> False
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()  # loop rechecks is_disconnected() -> True, generator ends
