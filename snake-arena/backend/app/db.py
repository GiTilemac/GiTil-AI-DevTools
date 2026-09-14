"""Database engine/session setup, configured via the DATABASE_URL
environment variable (defaulting to a local SQLite file).

Every query in this app goes through plain SQLAlchemy Core/ORM - no raw
SQL, no SQLite-specific syntax anywhere else in the app - so pointing
DATABASE_URL at a different backend (e.g. `postgresql+psycopg://...`
once a Postgres driver is added as a dependency) is the only change
needed to move databases.
"""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

DEFAULT_DATABASE_URL = "sqlite:///./snake_arena.db"

# SQLAlchemy's own spellings for "in-memory sqlite".
_MEMORY_SQLITE_URLS = {"sqlite://", "sqlite:///:memory:"}


class Base(DeclarativeBase):
    pass


def database_url_from_env() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def make_engine(database_url: str) -> Engine:
    """Builds an engine for `database_url`. SQLite needs two non-default
    settings to behave under a threaded server: a single shared
    connection for in-memory databases (each new connection otherwise
    gets its own blank database), and check_same_thread=False since
    FastAPI runs sync endpoints across a thread pool. Neither applies to
    other backends, so this is the only SQLite-specific code in the app.
    """
    connect_args: dict[str, object] = {}
    engine_kwargs: dict[str, object] = {}

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if database_url in _MEMORY_SQLITE_URLS or ":memory:" in database_url:
            engine_kwargs["poolclass"] = StaticPool

    return create_engine(database_url, connect_args=connect_args, **engine_kwargs)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
