"""
rootx.lang
==========
Language support for ROOT//X TOOLKIT.
Saves the user's language preference to the data directory.
"""

from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Optional


def _get_data_dir() -> Path:
    """Returns the toolkit's data directory (same as license.py)."""
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / "rootx-toolkit"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _lang_file() -> Path:
    return _get_data_dir() / "language.json"


def has_saved_language() -> bool:
    """Return True if user has previously saved a language choice."""
    return _lang_file().exists()


def get_active_language() -> str:
    """Return the saved language code, defaulting to 'en'."""
    try:
        with open(_lang_file(), "r", encoding="utf-8") as f:
            return json.load(f).get("lang", "en")
    except Exception:
        return "en"


def save_language(code: str) -> None:
    """Persist the language choice to disk."""
    try:
        with open(_lang_file(), "w", encoding="utf-8") as f:
            json.dump({"lang": code}, f)
    except Exception:
        pass


def load_language(code: Optional[str] = None) -> dict:
    """
    Load the STRINGS dict for the given language code.
    Falls back to English on any error.
    """
    if code is None:
        code = get_active_language()
    try:
        if code == "pl":
            from rootx.lang.pl import STRINGS
        else:
            from rootx.lang.en import STRINGS
        return STRINGS
    except Exception:
        from rootx.lang.en import STRINGS
        return STRINGS
