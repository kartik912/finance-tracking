"""Repository for the investments table."""
from __future__ import annotations

from models.investment import Investment
from observers.event_bus import Events
from repositories.base_repository import BaseRepository


class InvestmentRepository(BaseRepository[Investment]):
    """CRUD operations for :class:`~models.investment.Investment`."""

    def __init__(self) -> None:
        super().__init__(Investment, Events.INVESTMENT_WRITE)

    def get_by_type(self, investment_type: str) -> list[Investment]:
        """Return all investments matching *investment_type*, ordered by date DESC."""
        from config.database import SessionLocal
        session = SessionLocal()
        try:
            return (
                session.query(Investment)
                .filter(Investment.investment_type == investment_type)
                .order_by(Investment.date.desc(), Investment.id.desc())
                .all()
            )
        except Exception:
            session.rollback()
            raise
        finally:
            SessionLocal.remove()

    def get_all_ordered(self) -> list[Investment]:
        """Return all investments ordered by date DESC."""
        from config.database import SessionLocal
        session = SessionLocal()
        try:
            return (
                session.query(Investment)
                .order_by(Investment.date.desc(), Investment.id.desc())
                .all()
            )
        except Exception:
            session.rollback()
            raise
        finally:
            SessionLocal.remove()
