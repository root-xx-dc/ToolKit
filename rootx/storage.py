"""
rootx.storage
=============
Disk / storage diagnostics: usage of mounted volumes, partition listing,
free space, and a safe "find large files" helper (read-only, never deletes).

Cross-platform: uses `psutil` (Windows/macOS/Linux) for usage figures and
plain `os.walk` for the large-file scan, so no external command
(`df`, `find`, `lsblk`, ...) is required on any OS.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from . import utils

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None

WARNING_THRESHOLD = 80
CRITICAL_THRESHOLD = 90

# Filesystem types that don't represent real user storage and should be
# skipped when listing mounts (Linux/macOS pseudo-filesystems).
_SKIP_FSTYPES = {"tmpfs", "devtmpfs", "squashfs", "overlay", "autofs", "devfs"}


@dataclass
class MountUsage:
    mount_point: str
    filesystem: str = "N/A"
    size: str = "N/A"
    used: str = "N/A"
    available: str = "N/A"
    percent: Optional[int] = None

    @property
    def level(self) -> str:
        if self.percent is None:
            return "unknown"
        if self.percent >= CRITICAL_THRESHOLD:
            return "critical"
        if self.percent >= WARNING_THRESHOLD:
            return "warning"
        return "ok"


def get_df() -> List[MountUsage]:
    """Return per-volume usage for all real mounted filesystems/drives."""
    entries: List[MountUsage] = []
    if psutil is None:
        return entries

    try:
        partitions = psutil.disk_partitions(all=False)
    except Exception:
        return entries

    for part in partitions:
        if part.fstype and part.fstype.lower() in _SKIP_FSTYPES:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        entries.append(
            MountUsage(
                mount_point=part.mountpoint,
                filesystem=part.fstype or "N/A",
                size=utils.human_bytes(usage.total),
                used=utils.human_bytes(usage.used),
                available=utils.human_bytes(usage.free),
                percent=int(usage.percent),
            )
        )
    return entries


def get_lsblk() -> str:
    """Best-effort block-device / volume listing, per OS."""
    if utils.is_linux() and utils.command_exists("lsblk"):
        result = utils.run(["lsblk"], timeout=10)
        if result.ok:
            return result.stdout
    if utils.is_macos() and utils.command_exists("diskutil"):
        result = utils.run(["diskutil", "list"], timeout=10)
        if result.ok:
            return result.stdout
    if utils.is_windows():
        result = utils.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Disk | Format-Table Number,FriendlyName,Size,PartitionStyle -AutoSize | Out-String"],
            timeout=15,
        )
        if result.ok and result.stdout:
            return result.stdout
    return ""


def find_large_files(path: Optional[str] = None, min_mb: int = 100, limit: int = 25) -> List[str]:
    """
    Find files larger than `min_mb` under `path` using a pure-Python walk
    (read-only, never deletes, works identically on every OS).
    Returns a list of "size\tpath" strings, largest first.
    """
    if not path:
        path = str(Path.home())
    root = Path(path)
    if not root.exists():
        return []

    min_bytes = min_mb * 1024 * 1024
    scored = []
    try:
        for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(fpath)
                except OSError:
                    continue
                if size >= min_bytes:
                    scored.append((size, fpath))
            if len(scored) > 5000:  # safety cap so a huge tree can't hang the app
                break
    except Exception:
        pass

    scored.sort(key=lambda item: item[0], reverse=True)
    return [f"{utils.human_bytes(size)}\t{path_}" for size, path_ in scored[:limit]]


def diagnose() -> dict:
    """Return a summary suitable for Doctor: list of MountUsage plus flags."""
    mounts = get_df()
    warnings = [m for m in mounts if m.level == "warning"]
    criticals = [m for m in mounts if m.level == "critical"]
    return {
        "mounts": mounts,
        "warnings": warnings,
        "criticals": criticals,
    }
