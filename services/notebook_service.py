"""Business-logic layer for notebooks.

Sits between the screens and the repository layer. Never writes raw SQL.
"""
from __future__ import annotations

import threading
from datetime import datetime

from models.notebook import Notebook
from repositories.notebook_repository import NotebookRepository
from repositories.note_repository import NoteRepository
from services.cache_service import CacheService

_CACHE_KEY = "notebooks:all"


class NotebookService:
    """Singleton service for notebook CRUD operations."""

    _instance: NotebookService | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._repo = NotebookRepository()
        self._note_repo = NoteRepository()
        self._cache = CacheService.instance()

    # ------------------------------------------------------------------
    # Singleton factory
    # ------------------------------------------------------------------

    @classmethod
    def instance(cls) -> "NotebookService":
        """Return the shared singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_all(self) -> list[Notebook]:
        """Return all notebooks ordered newest first (LRU-cached)."""
        cached = self._cache.get_lru(_CACHE_KEY)
        if cached is not None:
            return cached
        result = self._repo.get_all_ordered()
        self._cache.set_lru(_CACHE_KEY, result)
        return result

    def get_note_count(self, notebook_id: int) -> int:
        """Return the number of notes in a notebook."""
        key = f"notebooks:count:{notebook_id}"
        cached = self._cache.get_lru(key)
        if cached is not None:
            return cached
        count = self._note_repo.count_by_notebook(notebook_id)
        self._cache.set_lru(key, count)
        return count

    def get_by_id(self, notebook_id: int) -> Notebook | None:
        """Return a single notebook by ID."""
        return self._repo.get_by_id(notebook_id)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add_notebook(self, name: str, color: str, emoji: str) -> Notebook:
        """Create and persist a new notebook.

        Raises:
            ValueError: If name is empty or exceeds 200 characters.
        """
        name = name.strip()
        if not name:
            raise ValueError("Notebook name cannot be empty.")
        if len(name) > 200:
            raise ValueError("Notebook name must be 200 characters or fewer.")

        notebook = Notebook(
            name=name,
            color=color or "#1E88E5",
            emoji=emoji or "\U0001f4d3",
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        saved = self._repo.insert(notebook)
        self._cache.invalidate("notebooks")
        return saved

    def update_notebook(
        self,
        notebook_id: int,
        name: str,
        color: str | None = None,
        emoji: str | None = None,
    ) -> Notebook | None:
        """Rename or re-color a notebook.

        Raises:
            ValueError: If name is empty or exceeds 200 characters.
        """
        name = name.strip()
        if not name:
            raise ValueError("Notebook name cannot be empty.")
        if len(name) > 200:
            raise ValueError("Notebook name must be 200 characters or fewer.")

        notebook = self._repo.get_by_id(notebook_id)
        if notebook is None:
            return None

        notebook.name = name
        if color is not None:
            notebook.color = color
        if emoji is not None:
            notebook.emoji = emoji

        updated = self._repo.update(notebook)
        self._cache.invalidate("notebooks")
        return updated

    def delete_notebook(self, notebook_id: int) -> None:
        """Delete a notebook and all its notes (CASCADE in DB)."""
        self._repo.delete(notebook_id)
        self._cache.invalidate("notebooks")
        self._cache.invalidate("notes")
