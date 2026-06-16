"""Tests for config/settings.py — AppConfig, load(), and save()."""
from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from config.settings import AppConfig, load, save


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_config_path(path: str):
    """Context manager that redirects _CONFIG_PATH to *path*."""
    return patch("config.settings._CONFIG_PATH", path)


# ---------------------------------------------------------------------------
# AppConfig dataclass
# ---------------------------------------------------------------------------

class TestAppConfig:
    def test_default_values(self) -> None:
        """AppConfig should have sensible defaults on instantiation."""
        cfg = AppConfig()
        assert cfg.gemini_api_key == ""
        assert cfg.theme_mode == "system"
        assert cfg.currency_symbol == "₹"
        assert cfg.extra == {}

    def test_custom_values(self) -> None:
        """AppConfig should store custom values correctly."""
        cfg = AppConfig(gemini_api_key="key", theme_mode="dark", currency_symbol="$")
        assert cfg.gemini_api_key == "key"
        assert cfg.theme_mode == "dark"
        assert cfg.currency_symbol == "$"

    def test_extra_field_defaults_to_empty_dict(self) -> None:
        """Two separate AppConfig instances must not share the same extra dict."""
        cfg1 = AppConfig()
        cfg2 = AppConfig()
        cfg1.extra["foo"] = "bar"
        assert "foo" not in cfg2.extra


# ---------------------------------------------------------------------------
# load()
# ---------------------------------------------------------------------------

class TestLoad:
    def test_returns_defaults_when_file_missing(self, config_path: str) -> None:
        """load() must return default AppConfig when config.json does not exist."""
        with _patch_config_path(config_path):
            cfg = load()
        assert cfg.gemini_api_key == ""
        assert cfg.theme_mode == "system"

    def test_reads_existing_config(self, existing_config: tuple[str, dict]) -> None:
        """load() must correctly parse a valid config.json."""
        path, data = existing_config
        with _patch_config_path(path):
            cfg = load()
        assert cfg.gemini_api_key == data["gemini_api_key"]
        assert cfg.theme_mode == data["theme_mode"]
        assert cfg.currency_symbol == data["currency_symbol"]
        assert cfg.db_path == data["db_path"]

    def test_returns_defaults_on_malformed_json(self, config_path: str) -> None:
        """load() must return defaults silently if config.json has invalid JSON."""
        with open(config_path, "w") as fh:
            fh.write("{not valid json}")
        with _patch_config_path(config_path):
            cfg = load()
        assert cfg.gemini_api_key == ""

    def test_unknown_keys_stored_in_extra(self, tmp_path) -> None:
        """load() must preserve unknown config keys inside cfg.extra."""
        path = str(tmp_path / "config.json")
        with open(path, "w") as fh:
            json.dump({"gemini_api_key": "k", "custom_flag": True}, fh)
        with _patch_config_path(path):
            cfg = load()
        assert cfg.extra.get("custom_flag") is True

    def test_partial_config_uses_defaults_for_missing_fields(self, tmp_path) -> None:
        """load() must apply defaults for fields absent from config.json."""
        path = str(tmp_path / "config.json")
        with open(path, "w") as fh:
            json.dump({"gemini_api_key": "only-key"}, fh)
        with _patch_config_path(path):
            cfg = load()
        assert cfg.gemini_api_key == "only-key"
        assert cfg.theme_mode == "system"
        assert cfg.currency_symbol == "₹"


# ---------------------------------------------------------------------------
# save()
# ---------------------------------------------------------------------------

class TestSave:
    def test_creates_config_file(self, config_path: str) -> None:
        """save() must create config.json if it does not exist."""
        cfg = AppConfig(gemini_api_key="new-key")
        with _patch_config_path(config_path):
            save(cfg)
        assert os.path.exists(config_path)

    def test_saved_values_are_correct(self, config_path: str) -> None:
        """save() must write all AppConfig fields to config.json."""
        cfg = AppConfig(gemini_api_key="abc", theme_mode="light", currency_symbol="€")
        with _patch_config_path(config_path):
            save(cfg)
        with open(config_path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["gemini_api_key"] == "abc"
        assert data["theme_mode"] == "light"
        assert data["currency_symbol"] == "€"

    def test_extra_keys_are_preserved(self, config_path: str) -> None:
        """save() must write cfg.extra keys alongside the known fields."""
        cfg = AppConfig(extra={"my_flag": 42})
        with _patch_config_path(config_path):
            save(cfg)
        with open(config_path, encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["my_flag"] == 42

    def test_round_trip(self, config_path: str) -> None:
        """save() followed by load() must return an equivalent AppConfig."""
        original = AppConfig(
            gemini_api_key="round-trip-key",
            theme_mode="dark",
            currency_symbol="£",
            extra={"version": 2},
        )
        with _patch_config_path(config_path):
            save(original)
            restored = load()
        assert restored.gemini_api_key == original.gemini_api_key
        assert restored.theme_mode == original.theme_mode
        assert restored.currency_symbol == original.currency_symbol
        assert restored.extra.get("version") == 2
