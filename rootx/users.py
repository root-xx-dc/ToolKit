"""
rootx.users
===========
User and group management.
Linux: /etc/passwd, /etc/group, passwd -l/-u.
Windows: PowerShell Get-LocalUser, Disable/Enable-LocalUser.

Exclusions: no userdel, no deluser, no password changes.
"""

from __future__ import annotations

import getpass
from dataclasses import dataclass, field
from typing import List

from . import utils


@dataclass
class UserInfo:
    username: str
    uid: int
    gid: int
    home: str
    shell: str
    full_name: str = ""
    locked: bool = False


@dataclass
class GroupInfo:
    name: str
    gid: int
    members: List[str] = field(default_factory=list)


def get_current_user() -> str:
    """Return the current user's username."""
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def list_users() -> List[UserInfo]:
    """List non-system users. Linux: UID >= 1000. Windows: local accounts."""
    users: List[UserInfo] = []
    if utils.is_linux():
        try:
            with open("/etc/passwd", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if len(parts) >= 7:
                        uid = int(parts[2]) if parts[2].isdigit() else -1
                        if uid >= 1000 and uid != 65534:  # exclude nobody
                            locked = parts[1].startswith("!")
                            users.append(
                                UserInfo(
                                    username=parts[0],
                                    uid=uid,
                                    gid=int(parts[3]) if parts[3].isdigit() else -1,
                                    full_name=parts[4].split(",")[0],
                                    home=parts[5],
                                    shell=parts[6],
                                    locked=locked,
                                )
                            )
        except Exception:
            pass
    elif utils.is_windows():
        result = utils.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-LocalUser | Select-Object Name,Enabled,Description | Format-Table -AutoSize",
            ],
            timeout=15,
        )
        lines = result.stdout.splitlines()
        if len(lines) > 3:
            for i, line in enumerate(lines[3:]):
                parts = line.split()
                if parts:
                    enabled = parts[1].lower() != "false" if len(parts) > 1 else True
                    users.append(
                        UserInfo(
                            username=parts[0],
                            uid=1000 + i,
                            gid=1000,
                            home="",
                            shell="",
                            locked=not enabled,
                        )
                    )
    return users


def list_groups() -> List[GroupInfo]:
    """List groups and their members."""
    groups: List[GroupInfo] = []
    if utils.is_linux():
        try:
            with open("/etc/group", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if len(parts) >= 4:
                        gid = int(parts[2]) if parts[2].isdigit() else -1
                        members = [m for m in parts[3].split(",") if m]
                        groups.append(GroupInfo(name=parts[0], gid=gid, members=members))
        except Exception:
            pass
    elif utils.is_windows():
        result = utils.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-LocalGroup | Select-Object Name,Description | Format-Table -AutoSize",
            ],
            timeout=15,
        )
        lines = result.stdout.splitlines()
        if len(lines) > 3:
            for i, line in enumerate(lines[3:]):
                parts = line.split(None, 1)
                if parts:
                    groups.append(GroupInfo(name=parts[0], gid=500 + i, members=[]))
    return groups


def lock_user(username: str) -> utils.CommandResult:
    """Lock a user account. Returns command result."""
    if utils.is_linux():
        prefix = utils.sudo_prefix()
        return utils.run(prefix + ["passwd", "-l", username], timeout=10)
    elif utils.is_windows():
        return utils.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Disable-LocalUser -Name '{username}'",
            ],
            timeout=15,
        )
    return utils.CommandResult(ok=False, error="Not supported on this platform.")


def unlock_user(username: str) -> utils.CommandResult:
    """Unlock a user account. Returns command result."""
    if utils.is_linux():
        prefix = utils.sudo_prefix()
        return utils.run(prefix + ["passwd", "-u", username], timeout=10)
    elif utils.is_windows():
        return utils.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Enable-LocalUser -Name '{username}'",
            ],
            timeout=15,
        )
    return utils.CommandResult(ok=False, error="Not supported on this platform.")
