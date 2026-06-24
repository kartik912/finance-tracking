"""Gemini AI service — Phase 6.1.

Wraps the google-genai 2.8.x client and persists conversation history to
SQLite via ChatMessageRepository. All API key access goes through AppConfig,
never hardcoded.

Architecture notes
------------------
* Singleton via :meth:`GeminiService.instance` — one client per process.
* The Gemini session is re-created lazily from persisted DB history whenever
  the singleton is rebuilt (e.g. after api-key config change), so conversation
  context survives app restarts.
* API errors are caught here and re-raised as :class:`GeminiError` so the chat
  screen never imports google.genai directly (layer boundary stays clean).
* No UI code — zero Flet imports.
"""
from __future__ import annotations

import threading
from datetime import datetime

import google.genai as genai
import google.genai.types as gtypes

from config.settings import load as load_config
from models.chat_message import ChatMessage
from repositories.chat_message_repository import ChatMessageRepository
from services.cache_service import CacheService

# ── constants ────────────────────────────────────────────────────────────────
_MODEL = "gemini-2.0-flash"
_SYSTEM_PROMPT = (
    "You are a helpful personal finance assistant embedded in a finance "
    "tracking app. The user tracks their income, expenses, investments, "
    "savings goals, and bill splits inside this app. Answer concisely and "
    "practically. When the user asks about their finances, remind them that "
    "you don't have direct access to their data unless they paste it — "
    "but you can help them interpret numbers, plan budgets, or explain "
    "financial concepts."
)
_HISTORY_CONTEXT_TURNS = 20   # how many past messages to send as context
_MAX_CONTENT_LENGTH = 32_000  # guard against accidental huge pastes


class GeminiError(Exception):
    """Raised when the Gemini API returns an error or is misconfigured."""


class GeminiService:
    """Singleton service for Gemini AI chat.

    Usage::

        svc = GeminiService.instance()
        reply = svc.send_message("How do I build an emergency fund?")
        history = svc.get_history()
        svc.clear_history()
    """

    _instance: GeminiService | None = None
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def instance(cls) -> GeminiService:
        """Return the application-wide singleton."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Destroy the singleton so the next call to :meth:`instance` rebuilds
        it with the latest API key from config. Call after the user saves a new
        key in the settings screen."""
        with cls._lock:
            cls._instance = None

    def __init__(self) -> None:
        self._repo = ChatMessageRepository()
        self._cache = CacheService.instance()
        self._client: genai.Client | None = None
        self._chat_session: genai.chats.Chat | None = None

    # ── public API ──────────────────────────────────────────────────────────

    def is_configured(self) -> bool:
        """Return True if a non-empty API key is stored in config."""
        return bool(load_config().gemini_api_key.strip())

    def get_history(self) -> list[ChatMessage]:
        """Return the full conversation history, oldest first."""
        key = "chat:history"
        cached = self._cache.get_lru(key)
        if cached is not None:
            return cached
        result = self._repo.get_all_ordered()
        self._cache.set_lru(key, result)
        return result

    def send_message(self, user_text: str) -> str:
        """Send *user_text* to Gemini and return the model's reply as a string.

        Persists both the user message and the model reply to the DB so
        history survives app restarts.

        Raises
        ------
        GeminiError
            If no API key is configured, the network request fails, or the
            model returns an empty response.
        ValueError
            If *user_text* is empty or exceeds ``_MAX_CONTENT_LENGTH``.
        """
        user_text = user_text.strip()
        if not user_text:
            raise ValueError("Message cannot be empty.")
        if len(user_text) > _MAX_CONTENT_LENGTH:
            raise ValueError(
                f"Message is too long ({len(user_text):,} chars). "
                f"Maximum is {_MAX_CONTENT_LENGTH:,} characters."
            )
        if not self.is_configured():
            raise GeminiError(
                "No Gemini API key configured. Go to Settings to add one."
            )

        # Persist the user message immediately (before API call)
        self._save_message("user", user_text)

        # Build / reuse chat session
        session = self._get_or_create_session()

        try:
            response = session.send_message(user_text)
        except Exception as exc:
            raise GeminiError(f"Gemini API error: {exc}") from exc

        reply = self._extract_text(response)
        if not reply:
            raise GeminiError("Gemini returned an empty response.")

        # Persist the model reply
        self._save_message("model", reply)
        return reply

    def clear_history(self) -> None:
        """Delete all persisted messages and reset the in-process session."""
        self._repo.clear_all()
        self._chat_session = None
        self._cache.invalidate("chat")

    # ── private helpers ─────────────────────────────────────────────────────

    def _get_or_create_session(self) -> genai.chats.Chat:
        """Return the live Gemini chat session, creating it if necessary.

        On first call (or after :meth:`clear_history`/key change), rebuilds
        the session from the last ``_HISTORY_CONTEXT_TURNS`` DB messages so
        Gemini has conversational context even after app restart.
        """
        if self._chat_session is not None:
            return self._chat_session

        cfg = load_config()
        if not cfg.gemini_api_key.strip():
            raise GeminiError("No Gemini API key configured.")

        self._client = genai.Client(api_key=cfg.gemini_api_key.strip())

        # Reconstruct history from DB (exclude the message we're about to send
        # — it was just saved, so get_last_n returns it as the last entry;
        # we slice it off so Gemini doesn't see a user turn with no reply yet).
        recent = self._repo.get_last_n(_HISTORY_CONTEXT_TURNS + 1)
        # Drop the last item — that's the user message we just saved and
        # haven't sent yet.
        history_rows = recent[:-1] if recent else []

        history = [
            gtypes.Content(
                role=msg.role,
                parts=[gtypes.Part(text=msg.content)],
            )
            for msg in history_rows
        ]

        self._chat_session = self._client.chats.create(
            model=_MODEL,
            config=gtypes.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
            ),
            history=history or None,
        )
        return self._chat_session

    def _save_message(self, role: str, content: str) -> None:
        """Persist a single message and invalidate the history cache."""
        msg = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )
        self._repo.insert(msg)
        self._cache.invalidate("chat")

    @staticmethod
    def _extract_text(response: gtypes.GenerateContentResponse) -> str:
        """Pull the plain-text reply out of a GenerateContentResponse."""
        try:
            return response.text or ""
        except Exception:  # noqa: BLE001
            # Fallback: iterate candidates manually
            try:
                return "".join(
                    part.text
                    for candidate in response.candidates
                    for part in candidate.content.parts
                    if hasattr(part, "text")
                )
            except Exception:  # noqa: BLE001
                return ""
