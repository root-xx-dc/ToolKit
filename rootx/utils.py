"""
rootx.utils
===========
Shared low-level helpers used across the whole toolkit:

* safe subprocess execution (never uses shell=True with untrusted input)
* OS detection (Windows / macOS / Linux) + distro / architecture detection
* byte / uptime formatting
* command existence checks
* privilege helpers (sudo on Unix, elevation notice on Windows)

All functions in this module are defensive: they must never raise an
unhandled exception up into the CLI layer. Callers get back a structured
result (CommandResult) instead of a raw exception whenever a subprocess is
involved.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional, Sequence


@dataclass
class CommandResult:
    """Structured result of a subprocess execution."""

    ok: bool
    stdout: str = ""
    stderr: str = ""
    returncode: Optional[int] = None
    error: Optional[str] = None
    command: str = field(default="")


# ---------------------------------------------------------------------------
# OS detection
# ---------------------------------------------------------------------------

def is_windows() -> bool:
    return platform.system() == "Windows"


def is_macos() -> bool:
    return platform.system() == "Darwin"


def is_linux() -> bool:
    return platform.system() == "Linux"


def os_name() -> str:
    """Human readable current OS label."""
    if is_windows():
        return "Windows"
    if is_macos():
        return "macOS"
    if is_linux():
        return "Linux"
    return platform.system() or "Unknown"


def command_exists(name: str) -> bool:
    """Return True if `name` is a resolvable executable on PATH."""
    try:
        return shutil.which(name) is not None
    except Exception:
        return False


def run(
    args: Sequence[str],
    timeout: int = 10,
    input_text: Optional[str] = None,
    check_exists: bool = True,
) -> CommandResult:
    """
    Run a command safely.

    - Never uses shell=True.
    - `args` must be a list/tuple of tokens (argv style), never a raw string
      built from user input.
    - Any failure (missing binary, timeout, permission error, etc.) is
      captured and returned as a CommandResult instead of raising.
    """
    cmd_str = " ".join(args)
    if not args:
        return CommandResult(ok=False, error="Empty command.", command=cmd_str)

    if check_exists and not command_exists(args[0]):
        return CommandResult(
            ok=False,
            error=f"Command not found: {args[0]}",
            command=cmd_str,
        )

    try:
        proc = subprocess.run(
            list(args),
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return CommandResult(
            ok=proc.returncode == 0,
            stdout=proc.stdout.strip() if proc.stdout else "",
            stderr=proc.stderr.strip() if proc.stderr else "",
            returncode=proc.returncode,
            command=cmd_str,
        )
    except FileNotFoundError:
        return CommandResult(ok=False, error=f"Command not found: {args[0]}", command=cmd_str)
    except PermissionError:
        return CommandResult(ok=False, error=f"Permission denied running: {args[0]}", command=cmd_str)
    except subprocess.TimeoutExpired:
        return CommandResult(ok=False, error=f"Command timed out: {cmd_str}", command=cmd_str)
    except Exception as exc:  # last-resort safety net, never crash the app
        return CommandResult(ok=False, error=f"Unexpected error: {exc}", command=cmd_str)


def is_root() -> bool:
    """True if running with elevated privileges (root on Unix, admin on Windows)."""
    try:
        if is_windows():
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False


def sudo_prefix() -> List[str]:
    """
    Return the privilege-escalation prefix for the current OS, or [] if the
    process is already elevated / none is available. On Windows there is no
    safe non-interactive equivalent to `sudo`, so an empty prefix is
    returned and the CLI layer instead warns the user to run the terminal
    "as Administrator" when an action needs it.
    """
    if is_root():
        return []
    if is_windows():
        return []
    if command_exists("sudo"):
        return ["sudo"]
    return []


def needs_admin_notice() -> Optional[str]:
    """On Windows, returns a notice to show before a privileged action."""
    if is_windows() and not is_root():
        return "This action may require running the terminal as Administrator."
    return None


# ---------------------------------------------------------------------------
# Distro / architecture detection
# ---------------------------------------------------------------------------

_DISTRO_ALIASES = {
    "ubuntu": "Ubuntu",
    "debian": "Debian",
    "kali": "Kali Linux",
    "linuxmint": "Linux Mint",
    "pop": "Pop!_OS",
    "arch": "Arch Linux",
    "manjaro": "Manjaro",
    "endeavouros": "EndeavourOS",
    "fedora": "Fedora",
    "rhel": "RHEL",
    "rocky": "Rocky Linux",
    "almalinux": "AlmaLinux",
    "opensuse": "openSUSE",
    "opensuse-leap": "openSUSE",
    "opensuse-tumbleweed": "openSUSE",
    "alpine": "Alpine Linux",
}


def detect_distro() -> dict:
    """
    Detect the OS "distribution" in a cross-platform way.
    Returns a dict with keys: id, name, version, id_like (never raises).
    On Linux this reads /etc/os-release; on macOS/Windows it uses `platform`.
    """
    info = {"id": "unknown", "name": "Unknown", "version": "", "id_like": ""}

    if is_windows():
        try:
            release, version, csd, ptype = platform.win32_ver()
            info["id"] = "windows"
            info["name"] = f"Windows {release}".strip()
            info["version"] = version or ""
        except Exception:
            info["id"] = "windows"
            info["name"] = "Windows"
        return info

    if is_macos():
        try:
            mac_release, _, _ = platform.mac_ver()
            info["id"] = "macos"
            info["name"] = "macOS"
            info["version"] = mac_release or ""
        except Exception:
            info["id"] = "macos"
            info["name"] = "macOS"
        return info

    # Linux
    try:
        if os.path.exists("/etc/os-release"):
            data = {}
            with open("/etc/os-release", "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    data[key] = value.strip('"')
            distro_id = data.get("ID", "unknown").lower()
            info["id"] = distro_id
            info["name"] = _DISTRO_ALIASES.get(distro_id, data.get("PRETTY_NAME", distro_id.title()))
            info["version"] = data.get("VERSION_ID", "")
            info["id_like"] = data.get("ID_LIKE", "")
    except Exception:
        pass
    return info


def detect_architecture() -> str:
    """Normalize platform.machine() into a common architecture label."""
    try:
        machine = platform.machine().lower()
    except Exception:
        return "unknown"

    mapping = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "aarch64": "aarch64",
        "arm64": "aarch64",
        "armv7l": "armhf",
        "armv6l": "armhf",
        "i686": "i686",
        "i386": "i686",
    }
    return mapping.get(machine, machine or "unknown")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def human_bytes(num_bytes: float) -> str:
    """Convert a byte count into a human readable string."""
    try:
        num_bytes = float(num_bytes)
    except (TypeError, ValueError):
        return "N/A"
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} EB"


def human_uptime(seconds: float) -> str:
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "N/A"
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def safe_read_file(path: str, max_bytes: int = 200_000) -> str:
    """Read a text file defensively, never raising."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read(max_bytes)
    except Exception:
        return ""


VALID_PACKAGE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+._-]*$")


def is_valid_package_name(name: str) -> bool:
    """Whitelist validation for package names before they touch a subprocess."""
    if not name or len(name) > 128:
        return False
    return bool(VALID_PACKAGE_NAME_RE.match(name))


def timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")
