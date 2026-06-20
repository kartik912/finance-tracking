"""Business-logic layer for notes, images, and doodles.

Handles validation, file path management, and delegates persistence
to the repository layer. Never writes raw SQL.
"""
from __future__ import annotations

import os
import threading
from datetime import datetime
from pathlib import Path

from models.note import Note
from models.note_doodle import NoteDoodle
from models.note_image import NoteImage
from repositories.note_doodle_repository import NoteDoodleRepository
from repositories.note_image_repository import NoteImageRepository
from repositories.note_repository import NoteRepository
from services.cache_service import CacheService

NOTE_TYPES = ["text", "image", "doodle"]

# App data directory: use a subfolder inside the project for desktop;
# override via environment variable for Android (set by Flet runtime).
_APP_DATA_DIR: str = os.environ.get(
    "FLET_APP_STORAGE_DATA",
    str(Path(__file__).resolve().parent.parent / "data"),
)


def get_app_data_dir() -> str:
    """Return the resolved app-data directory, creating it if needed."""
    path = os.environ.get("FLET_APP_STORAGE_DATA", _APP_DATA_DIR)
    os.makedirs(path, exist_ok=True)
    return path


class NoteService:
    """Singleton service for note, image, and doodle CRUD operations."""

    _instance: NoteService | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._repo = NoteRepository()
        self._img_repo = NoteImageRepository()
        self._doodle_repo = NoteDoodleRepository()
        self._cache = CacheService.instance()

    # ------------------------------------------------------------------
    # Singleton factory
    # ------------------------------------------------------------------

    @classmethod
    def instance(cls) -> "NoteService":
        """Return the shared singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ------------------------------------------------------------------
    # Note read operations
    # ------------------------------------------------------------------

    def get_notes_for_notebook(self, notebook_id: int) -> list[Note]:
        """Return all notes for a notebook, newest first (LRU-cached)."""
        key = f"notes:notebook:{notebook_id}"
        cached = self._cache.get_lru(key)
        if cached is not None:
            return cached
        result = self._repo.get_by_notebook(notebook_id)
        self._cache.set_lru(key, result)
        return result

    def get_note_by_id(self, note_id: int) -> Note | None:
        """Return a single note by ID."""
        return self._repo.get_by_id(note_id)

    # ------------------------------------------------------------------
    # Note write operations
    # ------------------------------------------------------------------

    def create_note(
        self, notebook_id: int, note_type: str, title: str = ""
    ) -> Note:
        """Create a new empty note of the given type.

        Raises:
            ValueError: For invalid notebook_id, note_type, or title length.
        """
        if notebook_id <= 0:
            raise ValueError("Invalid notebook_id.")
        if note_type not in NOTE_TYPES:
            raise ValueError(f"note_type must be one of {NOTE_TYPES}.")
        title = title.strip()
        if len(title) > 500:
            raise ValueError("Title must be 500 characters or fewer.")

        note = Note(
            notebook_id=notebook_id,
            title=title or "Untitled",
            content_text="",
            note_type=note_type,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        saved = self._repo.insert(note)
        self._cache.invalidate("notes")
        return saved

    def update_note_text(
        self, note_id: int, title: str, content_text: str
    ) -> Note | None:
        """Update the title and text content of a note.

        Raises:
            ValueError: If title or content exceeds allowed lengths.
        """
        title = title.strip()
        if len(title) > 500:
            raise ValueError("Title must be 500 characters or fewer.")
        if len(content_text) > 50_000:
            raise ValueError("Content must be 50,000 characters or fewer.")

        note = self._repo.get_by_id(note_id)
        if note is None:
            return None
        note.title = title or "Untitled"
        note.content_text = content_text
        updated = self._repo.update(note)
        self._cache.invalidate("notes")
        return updated

    def delete_note(self, note_id: int) -> None:
        """Delete a note and cascade-delete images/doodles from disk."""
        # Delete associated image files
        for img in self._img_repo.get_by_note(note_id):
            abs_path = self._abs_path(img.image_path)
            if os.path.isfile(abs_path):
                try:
                    os.remove(abs_path)
                except OSError:
                    pass

        # Delete associated doodle files
        for doodle in self._doodle_repo.get_by_note(note_id):
            abs_path = self._abs_path(doodle.doodle_path)
            if os.path.isfile(abs_path):
                try:
                    os.remove(abs_path)
                except OSError:
                    pass

        self._repo.delete(note_id)
        self._cache.invalidate("notes")

    # ------------------------------------------------------------------
    # Image operations
    # ------------------------------------------------------------------

    def get_images_for_note(self, note_id: int) -> list[NoteImage]:
        """Return all images attached to a note (LRU-cached)."""
        key = f"note_images:{note_id}"
        cached = self._cache.get_lru(key)
        if cached is not None:
            return cached
        result = self._img_repo.get_by_note(note_id)
        self._cache.set_lru(key, result)
        return result

    def add_image(self, note_id: int, source_abs_path: str) -> NoteImage:
        """Copy an image into the app data dir and record its relative path.

        Raises:
            ValueError: If source_abs_path is outside the file system.
        """
        source = Path(source_abs_path).resolve()
        if not source.is_file():
            raise ValueError(f"Source image not found: {source_abs_path}")

        data_dir = Path(get_app_data_dir())
        images_dir = data_dir / "note_images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Build a unique filename
        ext = source.suffix.lower() or ".jpg"
        unique_name = f"{note_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}{ext}"
        dest = images_dir / unique_name

        import shutil
        shutil.copy2(str(source), str(dest))

        # Store as relative path from data_dir
        rel_path = dest.relative_to(data_dir).as_posix()

        img_record = NoteImage(note_id=note_id, image_path=rel_path)
        saved = self._img_repo.insert(img_record)
        self._cache.invalidate("note_images")
        return saved

    def delete_image(self, image_id: int) -> None:
        """Delete a single image record and its file on disk."""
        img = self._img_repo.get_by_id(image_id)
        if img is not None:
            abs_path = self._abs_path(img.image_path)
            if os.path.isfile(abs_path):
                try:
                    os.remove(abs_path)
                except OSError:
                    pass
        self._img_repo.delete(image_id)
        self._cache.invalidate("note_images")

    def resolve_image_path(self, rel_path: str) -> str:
        """Return the absolute path for a stored relative image path."""
        return self._abs_path(rel_path)

    # ------------------------------------------------------------------
    # Doodle operations
    # ------------------------------------------------------------------

    def get_doodles_for_note(self, note_id: int) -> list[NoteDoodle]:
        """Return all doodles attached to a note (LRU-cached)."""
        key = f"note_doodles:{note_id}"
        cached = self._cache.get_lru(key)
        if cached is not None:
            return cached
        result = self._doodle_repo.get_by_note(note_id)
        self._cache.set_lru(key, result)
        return result

    def save_doodle(self, note_id: int, png_abs_path: str) -> NoteDoodle:
        """Record a doodle PNG file and move it into the app data directory.

        The caller is responsible for writing the PNG to ``png_abs_path``
        before calling this method.

        Raises:
            ValueError: If png_abs_path does not point to an existing file.
        """
        source = Path(png_abs_path).resolve()
        if not source.is_file():
            raise ValueError(f"Doodle PNG not found: {png_abs_path}")

        data_dir = Path(get_app_data_dir())
        doodles_dir = data_dir / "note_doodles"
        doodles_dir.mkdir(parents=True, exist_ok=True)

        unique_name = f"{note_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
        dest = doodles_dir / unique_name

        import shutil
        shutil.move(str(source), str(dest))

        rel_path = dest.relative_to(data_dir).as_posix()

        doodle_record = NoteDoodle(note_id=note_id, doodle_path=rel_path)
        saved = self._doodle_repo.insert(doodle_record)
        self._cache.invalidate("note_doodles")
        return saved

    def delete_doodle(self, doodle_id: int) -> None:
        """Delete a doodle record and its PNG file."""
        doodle = self._doodle_repo.get_by_id(doodle_id)
        if doodle is not None:
            abs_path = self._abs_path(doodle.doodle_path)
            if os.path.isfile(abs_path):
                try:
                    os.remove(abs_path)
                except OSError:
                    pass
        self._doodle_repo.delete(doodle_id)
        self._cache.invalidate("note_doodles")

    def resolve_doodle_path(self, rel_path: str) -> str:
        """Return the absolute path for a stored relative doodle path."""
        return self._abs_path(rel_path)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _abs_path(self, rel_path: str) -> str:
        """Reconstruct absolute path from a stored relative path."""
        data_dir = Path(get_app_data_dir())
        return str((data_dir / rel_path).resolve())
