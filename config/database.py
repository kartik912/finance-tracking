"""SQLAlchemy engine, session factory, and declarative base for the app.

Usage
-----
Call ``init_db(path)`` once from ``main.py`` before any repository is used.
All ORM models import ``Base`` from this module to register their tables.
"""
from __future__ import annotations

import os
import threading

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker


# ---------------------------------------------------------------------------
# Shared declarative base — every ORM model must subclass this
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Project-wide SQLAlchemy declarative base."""


# ---------------------------------------------------------------------------
# Module-level singletons (set by init_db)
# ---------------------------------------------------------------------------
engine: Engine | None = None
SessionLocal: scoped_session | None = None  # type: ignore[type-arg]

_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_db(path: str) -> None:
    """Initialize the engine and scoped session factory.

    Must be called from ``main.py`` before any repository or service is used.
    Calling it more than once is safe — subsequent calls are no-ops.
    """
    global engine, SessionLocal

    with _lock:
        if engine is not None:
            return  # already initialized

        db_dir = os.path.dirname(os.path.abspath(path))
        os.makedirs(db_dir, exist_ok=True)

        _engine = create_engine(
            f"sqlite:///{path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )

        # Apply SQLite pragmas on every new connection
        @event.listens_for(_engine, "connect")
        def _set_pragmas(dbapi_conn, _record) -> None:  # type: ignore[type-arg]
            """Enable WAL mode and foreign-key enforcement."""
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        SessionFactory = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
        engine = _engine
        SessionLocal = scoped_session(SessionFactory)


def get_engine() -> Engine:
    """Return the configured engine, falling back to a default path if needed."""
    if engine is None:
        default_path = os.path.join(
            os.path.expanduser("~"), ".finance_tracking_app", "finance.db"
        )
        init_db(default_path)
    return engine  # type: ignore[return-value]


def get_session() -> scoped_session:  # type: ignore[type-arg]
    """Return the thread-local scoped session.

    Callers must call ``SessionLocal.remove()`` when the unit of work is done.
    """
    if SessionLocal is None:
        get_engine()  # triggers init_db fallback
    return SessionLocal  # type: ignore[return-value]


def reset_db() -> None:
    """Tear down the current engine and session factory.

    **For use in tests only.** Clears the module-level singletons so that a
    subsequent ``init_db()`` call creates a fresh engine (e.g. ``:memory:``).
    """
    global engine, SessionLocal
    with _lock:
        if SessionLocal is not None:
            SessionLocal.remove()
        engine = None
        SessionLocal = None


def create_tables() -> None:
    """Create all ORM-mapped tables that do not already exist.

    Lazily imports every model module so their classes register themselves
    with ``Base.metadata`` before ``create_all`` is called.
    """
    import models.category  # noqa: F401
    import models.chat_message  # noqa: F401
    import models.debt  # noqa: F401
    import models.goal  # noqa: F401
    import models.investment  # noqa: F401
    import models.note  # noqa: F401
    import models.note_doodle  # noqa: F401
    import models.note_image  # noqa: F401
    import models.notebook  # noqa: F401
    import models.person  # noqa: F401
    import models.split  # noqa: F401
    import models.transaction  # noqa: F401

    Base.metadata.create_all(get_engine(), checkfirst=True)


def run_migration(target_version: int) -> None:
    """Apply incremental schema migrations up to *target_version*.

    Add a new ``elif current == N:`` block for each future schema change.
    Each block must execute the DDL and increment the version counter.
    """
    eng = get_engine()

    with eng.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
        ))
        row = conn.execute(text("SELECT version FROM schema_version")).fetchone()

        if row is None:
            conn.execute(text("INSERT INTO schema_version (version) VALUES (1)"))
            current = 1
        else:
            current = row[0]

        while current < target_version:
            if current == 1:
                # Placeholder for v1 → v2; add real DDL here when needed:
                # conn.execute(text("ALTER TABLE transactions ADD COLUMN notes TEXT"))
                conn.execute(text("UPDATE schema_version SET version = 2"))
                current = 2
            else:
                break  # no migration defined for this version
