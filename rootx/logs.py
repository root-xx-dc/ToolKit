"""
rootx.logs
==========
Log viewer for system logs.
Linux: journald + /var/log/ files.
Windows: PowerShell Get-EventLog / Get-WinEvent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from . import utils


@dataclass
class LogSource:
    name: str
    description: str
    available: bool


LEVEL_MAP_JOURNALD = {"critical": "2", "error": "3", "warning": "4", "info": "6"}
LEVEL_MAP_WINDOWS = {"critical": "Error", "error": "Error", "warning": "Warning", "info": "Information"}


def get_sources() -> List[LogSource]:
    """Return available log sources for the current OS."""
    sources: List[LogSource] = []
    if utils.is_linux():
        sources.append(LogSource("journald", "systemd journal", utils.command_exists("journalctl")))
        sources.append(LogSource("syslog", "/var/log/syslog", os.path.exists("/var/log/syslog")))
        sources.append(LogSource("auth", "/var/log/auth.log", os.path.exists("/var/log/auth.log")))
        sources.append(LogSource("kern", "/var/log/kern.log", os.path.exists("/var/log/kern.log")))
    elif utils.is_windows():
        sources.append(LogSource("System", "Windows System Event Log", True))
        sources.append(LogSource("Application", "Windows Application Event Log", True))
        sources.append(LogSource("Security", "Windows Security Event Log", True))
    return sources


def read_journal(level: str = "info", lines: int = 50) -> str:
    """Read journald logs filtered by priority level."""
    if not utils.is_linux() or not utils.command_exists("journalctl"):
        return "journald not available on this system."
    priority = LEVEL_MAP_JOURNALD.get(level.lower(), "6")
    result = utils.run(["journalctl", "-p", priority, "-n", str(lines), "--no-pager"], timeout=15)
    return result.stdout or result.error or "No output."


def read_file(path: str, lines: int = 50) -> str:
    """Tail of a log file."""
    if not utils.is_linux():
        return "File log reading only available on Linux."
    if utils.command_exists("tail"):
        result = utils.run(["tail", "-n", str(lines), path], timeout=10)
        return result.stdout or result.error or "Could not read file."
    return utils.safe_read_file(path)


def read_service_logs(name: str, lines: int = 50) -> str:
    """Read logs for a specific service via journald or EventLog on Windows."""
    if utils.is_linux() and utils.command_exists("journalctl"):
        result = utils.run(["journalctl", "-u", name, "-n", str(lines), "--no-pager"], timeout=15)
        return result.stdout or result.error or "No output."
    elif utils.is_windows():
        result = utils.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-EventLog -LogName Application -Source '*{name}*' -Newest {lines} | Format-List",
            ],
            timeout=20,
        )
        return result.stdout or result.error or "No output."
    return "Service logs not available on this system."


def read_windows_eventlog(log_name: str = "System", level: str = "warning", lines: int = 50) -> str:
    """Read Windows Event Log via PowerShell."""
    if not utils.is_windows():
        return "Windows Event Log only available on Windows."
    etype = LEVEL_MAP_WINDOWS.get(level.lower(), "Warning")
    result = utils.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Get-EventLog -LogName {log_name} -EntryType {etype} -Newest {lines} | Format-Table TimeGenerated,Source,Message -AutoSize",
        ],
        timeout=20,
    )
    return result.stdout or result.error or "No output."


def list_varlog_files() -> List[str]:
    """List files in /var/log/ (Linux only)."""
    if not utils.is_linux():
        return []
    try:
        return sorted(
            f for f in os.listdir("/var/log/")
            if os.path.isfile(f"/var/log/{f}") and not f.endswith(".gz")
        )
    except Exception:
        return []
