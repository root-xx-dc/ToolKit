"""
rootx.env_manager
=================
Environment variable management.
Linux: shell config files (.bashrc, .zshrc, .profile)
Windows: [Environment]::SetEnvironmentVariable via PowerShell
"""

from __future__ import annotations

import os
import re
from typing import List, Optional, Tuple

from . import utils

_SENSITIVE_KEYS = re.compile(r"(TOKEN|KEY|SECRET|PASSWORD|PASS)", re.IGNORECASE)


def list_env(filter_str: str = "") -> List[Tuple[str, str]]:
    """List environment variables. Mask sensitive values as ***."""
    items: List[Tuple[str, str]] = []
    for k, v in sorted(os.environ.items()):
        if filter_str and filter_str.lower() not in k.lower():
            continue
        masked_v = "***" if _SENSITIVE_KEYS.search(k) else v
        items.append((k, masked_v))
    return items


def get_shell_config() -> Optional[str]:
    """Detect the active shell config file on Linux."""
    if not utils.is_linux():
        return None
    home = os.path.expanduser("~")
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        candidates = [".zshrc", ".zprofile"]
    elif "bash" in shell:
        candidates = [".bashrc", ".bash_profile"]
    else:
        candidates = [".bashrc", ".zshrc", ".profile"]
    for c in candidates:
        p = os.path.join(home, c)
        if os.path.exists(p):
            return p
    return os.path.join(home, ".profile")


def add_to_path(directory: str) -> Tuple[bool, str]:
    """Append directory to PATH in shell config (Linux) or User PATH (Windows)."""
    directory = os.path.expanduser(directory)
    if utils.is_linux():
        config = get_shell_config()
        if not config:
            return False, "Could not detect shell config file."
        line = f'\nexport PATH="$PATH:{directory}"\n'
        try:
            with open(config, "a", encoding="utf-8") as f:
                f.write(line)
            return True, f"Added to PATH in {config}. Restart your shell to apply."
        except Exception as e:
            return False, str(e)
    elif utils.is_windows():
        result = utils.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"$p = [Environment]::GetEnvironmentVariable('PATH','User'); "
                f"[Environment]::SetEnvironmentVariable('PATH', $p + ';{directory}', 'User')",
            ],
            timeout=15,
        )
        if result.ok:
            return True, f"Added {directory} to User PATH. Restart your shell to apply."
        return False, result.error or result.stderr or "Failed."
    return False, "Not supported on this platform."


def set_variable(key: str, value: str) -> Tuple[bool, str]:
    """Set an environment variable persistently."""
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
        return False, "Invalid variable name."
    if utils.is_linux():
        config = get_shell_config()
        if not config:
            return False, "Could not detect shell config file."
        line = f'\nexport {key}="{value}"\n'
        try:
            with open(config, "a", encoding="utf-8") as f:
                f.write(line)
            return True, f"Set {key} in {config}. Restart your shell to apply."
        except Exception as e:
            return False, str(e)
    elif utils.is_windows():
        result = utils.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"[Environment]::SetEnvironmentVariable('{key}', '{value}', 'User')",
            ],
            timeout=15,
        )
        if result.ok:
            return True, f"Set {key} for current user."
        return False, result.error or result.stderr or "Failed."
    return False, "Not supported on this platform."


def remove_variable(key: str) -> Tuple[bool, str]:
    """Remove an environment variable from shell config (Linux) or registry (Windows)."""
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
        return False, "Invalid variable name."
    if utils.is_linux():
        config = get_shell_config()
        if not config:
            return False, "Could not detect shell config file."
        try:
            with open(config, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = [l for l in lines if not re.match(rf"^export {re.escape(key)}=", l.strip())]
            if len(new_lines) == len(lines):
                return False, f"{key} not found in {config}."
            with open(config, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            return True, f"Removed {key} from {config}."
        except Exception as e:
            return False, str(e)
    elif utils.is_windows():
        result = utils.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"[Environment]::SetEnvironmentVariable('{key}', $null, 'User')",
            ],
            timeout=15,
        )
        if result.ok:
            return True, f"Removed {key} from user environment."
        return False, result.error or result.stderr or "Failed."
    return False, "Not supported on this platform."


def windows_set(key: str, value: str, scope: str = "User") -> Tuple[bool, str]:
    """Windows-specific: set env var with explicit scope (User/Machine)."""
    if not utils.is_windows():
        return False, "Windows only."
    if scope not in ("User", "Machine"):
        return False, "Scope must be 'User' or 'Machine'."
    result = utils.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"[Environment]::SetEnvironmentVariable('{key}', '{value}', '{scope}')",
        ],
        timeout=15,
    )
    if result.ok:
        return True, f"Set {key}={value} in {scope} scope."
    return False, result.error or result.stderr or "Failed."
