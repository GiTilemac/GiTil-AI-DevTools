from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from app.game import TICK_INTERVAL_MS
from app.store import store

router = APIRouter(prefix="/watch", tags=["watch"])

_INTERVAL_S = TICK_INTERVAL_MS / 1000


def _format_sse(payload: str) -> str:
    return f"data: {payload}\n\n"


async def _event_stream(request: Request) -> AsyncIterator[str]:
    # Fires immediately with the current state, then again on every tick,
    # mirroring `backendClient.watch.subscribe` in the frontend mock.
    while True:
        if await request.is_disconnected():
            break
        state = await store.tick_watch()
        yield _format_sse(state.model_dump_json(by_alias=True))
        await asyncio.sleep(_INTERVAL_S)


@router.get("/live")
async def watch_live(request: Request) -> StreamingResponse:
    return StreamingResponse(_event_stream(request), media_type="text/event-stream")
