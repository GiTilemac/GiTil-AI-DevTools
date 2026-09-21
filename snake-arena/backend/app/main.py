from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routers import auth, leaderboard, watch

app = FastAPI(title="Snake Arena Backend API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(leaderboard.router)
app.include_router(watch.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Serves the built frontend (see ../Dockerfile, which builds frontend/ and
# copies its `dist/` output here as `static/`). Absent when running the
# backend standalone outside Docker - the API still works fine without it.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="frontend-assets")

    @app.exception_handler(StarletteHTTPException)
    async def spa_fallback(request: Request, exc: StarletteHTTPException) -> Response:
        # Client-side routes (e.g. /play, /login) have no matching API route
        # and would otherwise 404 on a hard refresh or direct link - serve
        # the SPA shell instead and let react-router take over. Non-GET or
        # non-HTML-accepting 404s (e.g. a bad API call) still 404 normally.
        # Note: this can't rescue GET /leaderboard specifically, since that
        # exact path is also a real API endpoint and always wins.
        if (
            exc.status_code == 404
            and request.method == "GET"
            and "text/html" in request.headers.get("accept", "")
        ):
            return FileResponse(STATIC_DIR / "index.html")
        return await http_exception_handler(request, exc)
