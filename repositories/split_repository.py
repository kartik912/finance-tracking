"""Repository for the splits table."""
from __future__ import annotations

from models.split import Split
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class SplitRepository(BaseRepository[Split]):
    """CRUD operations for :class:`~models.split.Split`.

    Standard CRUD is inherited from :class:`~repositories.base_repository.BaseRepository`.
    """

    def __init__(self) -> None:
        super().__init__(Split, Events.SPLIT_WRITE)

    def get_recent(self, limit: int = 100) -> list[Split]:
        """Return at most *limit* splits ordered by date DESC, then id DESC."""
        from config.database import SessionLocal
        session = SessionLocal()
        try:
            return (
                session.query(Split)
                .order_by(Split.date.desc(), Split.id.desc())
                .limit(limit)
                .all()
            )
        except Exception:
            session.rollback()
            raise
        finally:
            SessionLocal.remove()
