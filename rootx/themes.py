"""
rootx.themes
============
Terminal color theme system for ROOT//X TOOLKIT.
Theme is saved in the data directory as theme.json.
"""
from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Dict, Optional


THEMES: Dict[str, Dict[str, str]] = {
    "cyberpunk": {
        "name":    "Cyberpunk Cyan",
        "primary": "\033[96m",   # bright cyan
        "success": "\033[92m",   # bright green
        "warning": "\033[93m",   # bright yellow
        "error":   "\033[91m",   # bright red
        "dim":     "\033[2m",
        "bold":    "\033[1m",
        "reset":   "\033[0m",
        "white":   "\033[97m",
    },
    "matrix": {
        "name":    "Matrix Green",
        "primary": "\033[92m",
        "success": "\033[32m",
        "warning": "\033[93m",
        "error":   "\033[91m",
        "dim":     "\033[2m",
        "bold":    "\033[1m",
        "reset":   "\033[0m",
        "white":   "\033[97m",
    },
    "crimson": {
        "name":    "Crimson Red",
        "primary": "\033[91m",
        "success": "\033[92m",
        "warning": "\033[93m",
        "error":   "\033[31m",
        "dim":     "\033[2m",
        "bold":    "\033[1m",
        "reset":   "\033[0m",
        "white":   "\033[97m",
    },
    "purple": {
        "name":    "Deep Purple",
        "primary": "\033[35m",
        "success": "\033[92m",
        "warning": "\033[93m",
        "error":   "\033[91m",
        "dim":     "\033[2m",
        "bold":    "\033[1m",
        "reset":   "\033[0m",
        "white":   "\033[97m",
    },
    "mono": {
        "name":    "Monochrome Minimal",
        "primary": "\033[97m",
        "success": "\033[97m",
        "warning": "\033[37m",
        "error":   "\033[37m",
        "dim":     "\033[2m",
        "bold":    "\033[1m",
        "reset":   "\033[0m",
        "white":   "\033[97m",
    },
}

THEME_KEYS = list(THEMES.keys())  # ordered for menu


def _get_data_dir() -> Path:
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


def _theme_file() -> Path:
    return _get_data_dir() / "theme.json"


def get_active_theme_id() -> str:
    """Return saved theme ID, defaulting to 'cyberpunk'."""
    try:
        with open(_theme_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
            tid = data.get("theme", "cyberpunk")
            return tid if tid in THEMES else "cyberpunk"
    except Exception:
        return "cyberpunk"


def save_theme(theme_id: str) -> None:
    """Persist theme choice to disk."""
    try:
        with open(_theme_file(), "w", encoding="utf-8") as f:
            json.dump({"theme": theme_id}, f)
    except Exception:
        pass


def get_theme(theme_id: Optional[str] = None) -> Dict[str, str]:
    """Return theme dict for the given ID. Falls back to cyberpunk."""
    if theme_id is None:
        theme_id = get_active_theme_id()
    return THEMES.get(theme_id, THEMES["cyberpunk"])


def get_active_theme() -> Dict[str, str]:
    """Return the currently active theme dict."""
    return get_theme(get_active_theme_id())
