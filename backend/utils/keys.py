"""Utilities for retrieving API keys from the environment (optionally via `.env`).

Goal: adding a new key should not require copy/pasting a whole new function.

Use `get_secret("SOME_ENV_VAR")`, or keep small wrapper functions for common keys.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    # Included in this repo's dependencies (see pyproject.toml).
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore[assignment]

_DOTENV_LOADED = False


def _project_root() -> Path:
    # backend/utils/keys.py -> backend/ -> repo root
    return Path(__file__).resolve().parents[2]


def _ensure_dotenv_loaded() -> None:
    """Load `.env` files exactly once (best effort).

    This is explicit and deterministic compared to scraping shell rc files.
    """
    global _DOTENV_LOADED
    if _DOTENV_LOADED or load_dotenv is None:
        return

    # Project-local env files (should be gitignored).
    root = _project_root()
    load_dotenv(root / ".env", override=False)
    load_dotenv(root / ".env.local", override=False)

    # Optional per-user config (not tied to a specific shell).
    load_dotenv(Path.home() / ".config" / "draw-steel" / ".env", override=False)

    _DOTENV_LOADED = True


def get_secret(
    name: str,
) -> Optional[str]:
    """Get an env var from `os.environ`, optionally loading `.env` files once."""
    value = os.getenv(name)
    if value:
        return value

    _ensure_dotenv_loaded()
    value = os.getenv(name)
    if value:
        return value

    return None


def get_openrouter_api_key() -> Optional[str]:
    """Get OPENROUTER_API_KEY from environment / dotenv."""
    return get_secret("OPENROUTER_API_KEY")


def get_hf_token() -> Optional[str]:
    """Get HF_TOKEN from environment / dotenv."""
    return get_secret("HF_TOKEN")


def get_gemini_api_key() -> Optional[str]:
    """Get GEMINI_API_KEY from environment / dotenv."""
    return get_secret("GEMINI_API_KEY")
