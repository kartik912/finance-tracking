"""Unit tests for GeminiService — configuration checks, input validation, error handling."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from config.settings import AppConfig
from services.gemini_service import GeminiError, GeminiService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(key: str) -> AppConfig:
    """Return an AppConfig with the given gemini_api_key."""
    return AppConfig(gemini_api_key=key)


# ---------------------------------------------------------------------------
# is_configured
# ---------------------------------------------------------------------------

class TestIsConfigured:
    def test_true_when_key_is_present(self, fresh_db) -> None:
        with patch("services.gemini_service.load_config", return_value=_cfg("real-key-abc")):
            svc = GeminiService()
            assert svc.is_configured() is True

    def test_false_when_key_is_empty_string(self, fresh_db) -> None:
        with patch("services.gemini_service.load_config", return_value=_cfg("")):
            svc = GeminiService()
            assert svc.is_configured() is False

    def test_false_when_key_is_whitespace_only(self, fresh_db) -> None:
        with patch("services.gemini_service.load_config", return_value=_cfg("   ")):
            svc = GeminiService()
            assert svc.is_configured() is False


# ---------------------------------------------------------------------------
# send_message — input validation (ValueError)
# ---------------------------------------------------------------------------

class TestSendMessageValidation:
    def test_empty_string_raises_value_error(self, fresh_db) -> None:
        svc = GeminiService()
        with pytest.raises(ValueError, match="[Ee]mpty|cannot be empty"):
            svc.send_message("")

    def test_whitespace_only_raises_value_error(self, fresh_db) -> None:
        """send_message strips before checking, so whitespace-only == empty."""
        svc = GeminiService()
        with pytest.raises(ValueError, match="[Ee]mpty|cannot be empty"):
            svc.send_message("   ")

    def test_message_over_32000_chars_raises_value_error(self, fresh_db) -> None:
        svc = GeminiService()
        with pytest.raises(ValueError, match="[Tt]oo long|Maximum"):
            svc.send_message("x" * 32_001)

    def test_message_at_exactly_32000_chars_does_not_raise_value_error(
        self, fresh_db
    ) -> None:
        """Exactly 32 000 chars must NOT raise ValueError — only GeminiError (no key)."""
        with patch("services.gemini_service.load_config", return_value=_cfg("")):
            svc = GeminiService()
            with pytest.raises(GeminiError):
                svc.send_message("x" * 32_000)


# ---------------------------------------------------------------------------
# send_message — GeminiError when no API key
# ---------------------------------------------------------------------------

class TestSendMessageNoKey:
    def test_raises_gemini_error_when_key_absent(self, fresh_db) -> None:
        with patch("services.gemini_service.load_config", return_value=_cfg("")):
            svc = GeminiService()
            with pytest.raises(GeminiError, match="[Aa][Pp][Ii] key|configured"):
                svc.send_message("hello")

    def test_raises_gemini_error_when_key_whitespace(self, fresh_db) -> None:
        with patch("services.gemini_service.load_config", return_value=_cfg("   ")):
            svc = GeminiService()
            with pytest.raises(GeminiError):
                svc.send_message("hello")
