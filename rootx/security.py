"""
rootx.security
==============
Centralizes the safety rules that the rest of the toolkit must respect:

* a denylist of destructive command fragments that ROOT//X will never
  construct or execute, under any circumstances (extra defense in depth
  on top of the fact that every mutating action already goes through an
  explicit user confirmation).
* a helper to describe a privileged action to the user before running it.

Covers destructive fragments across Linux, macOS and Windows shells.
"""

from __future__ import annotations

from typing import List, Sequence

from . import utils

# Fragments that must never appear in a command ROOT//X builds internally.
# This is a defense-in-depth safety net; the higher-level modules already
# only ever construct a small, fixed set of known-safe commands.
DENYLIST_FRAGMENTS = [
    # Unix / Linux / macOS
    "rm -rf /",
    "mkfs",
    "dd if=",
    "fdisk",
    "parted",
    ":(){:|:&};:",  # fork bomb
    "userdel",
    "deluser",
    "chmod -R 777 /",
    "chown -R",
    "> /dev/sda",
    "iptables -F",
    "ufw disable",
    "systemctl disable firewalld",
    "grub-install",
    "update-grub",
    "passwd root",
    "diskutil eraseDisk",
    "diskutil partitiondisk",
    "launchctl remove",
    # Windows
    "format c:",
    "del /f /s /q c:\\",
    "rmdir /s /q c:\\",
    "diskpart",
    "vssadmin delete shadows",
    "bcdedit",
    "net user administrator",
    "reg delete hklm",
    "cipher /w",
]


def is_dangerous(command: Sequence[str]) -> bool:
    """Return True if the joined command matches any denylisted fragment."""
    joined = " ".join(command).lower()
    return any(fragment.lower() in joined for fragment in DENYLIST_FRAGMENTS)


def describe_privileged_action(command: List[str]) -> str:
    """Human readable description shown before any privilege-requiring action."""
    if utils.is_windows():
        return (
            "This operation may require an elevated (Administrator) terminal.\n\n"
            f"Proposed command:\n\n{' '.join(command)}"
        )
    return (
        "This operation requires administrator privileges.\n\n"
        f"Proposed command:\n\nsudo {' '.join(command)}"
    )
