"""Application configuration layer.

Loads and saves ``config.json`` at runtime. No secrets are ever hardcoded here.

Typical ``config.json`` structure::

    {
        "gemini_api_key": "YOUR_KEY_HERE",
        "db_path": "database/finance.db",
        "theme_mode": "system",
        "currency_symbol": "₹"
    }

Usage::

    from config.settings import AppConfig, load, save

    cfg = load()
    cfg.gemini_api_key = "new-key"
    save(cfg)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

# Path to config.json — sits next to main.py, never committed (in .gitignore)
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")
_CONFIG_PATH = os.path.normpath(_CONFIG_PATH)


@dataclass
class AppConfig:
    """Runtime configuration for the Finance Tracking App.

    All fields have sensible defaults so the app works even on first launch
    before the user has configured anything.
    """

    gemini_api_key: str = ""
    db_path: str = os.path.join("database", "finance.db")
    theme_mode: str = "system"      # "light" | "dark" | "system"
    currency_symbol: str = "₹"
    extra: dict[str, object] = field(default_factory=dict)


def load() -> AppConfig:
    """Read ``config.json`` and return an :class:`AppConfig` instance.

    If the file does not exist or is malformed, returns a default
    :class:`AppConfig` so the app can still start up.
    """
    if not os.path.exists(_CONFIG_PATH):
        return AppConfig()

    try:
        with open(_CONFIG_PATH, encoding="utf-8") as fh:
            data: dict[str, object] = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return AppConfig()

    known_fields = {"gemini_api_key", "db_path", "theme_mode", "currency_symbol"}
    known = {k: v for k, v in data.items() if k in known_fields}
    extra = {k: v for k, v in data.items() if k not in known_fields}

    return AppConfig(**known, extra=extra)


def save(config: AppConfig) -> None:
    """Write *config* back to ``config.json``.

    Creates the file if it does not exist.
    Preserves any unknown keys stored in ``config.extra``.
    """
    data: dict[str, object] = {
        "gemini_api_key": config.gemini_api_key,
        "db_path": config.db_path,
        "theme_mode": config.theme_mode,
        "currency_symbol": config.currency_symbol,
        **config.extra,
    }

    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
