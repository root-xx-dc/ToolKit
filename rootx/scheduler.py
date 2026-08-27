"""
rootx.scheduler
===============
Cron / Task Scheduler management.
Linux: crontab parsing and editing.
Windows: PowerShell Get-ScheduledTask.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

from . import security, utils


@dataclass
class CronJob:
    index: int
    schedule: str   # e.g. "*/5 * * * *"
    command: str
    raw: str
    comment: str = ""


@dataclass
class WindowsTask:
    name: str
    state: str
    last_run: str
    next_run: str
    trigger: str


_SCHEDULE_RE = re.compile(
    r"^(@(annually|yearly|monthly|weekly|daily|hourly|reboot)|"
    r"((\*|\d+|\d+-\d+|\d+/\d+)(,\*|,\d+|,\d+-\d+|,\d+/\d+)*\s+){4}"
    r"(\*|\d+|\d+-\d+|\d+/\d+)(,\*|,\d+|,\d+-\d+|,\d+/\d+)*)$"
)


def _is_valid_schedule(schedule: str) -> bool:
    return bool(_SCHEDULE_RE.match(schedule.strip()))


def list_jobs() -> List[CronJob]:
    """List current user's crontab entries."""
    if not utils.is_linux():
        return []
    result = utils.run(["crontab", "-l"], timeout=10)
    if not result.ok and "no crontab" in (result.stderr or "").lower():
        return []
    jobs: List[CronJob] = []
    idx = 0
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 5)
        if len(parts) >= 6:
            schedule = " ".join(parts[:5])
            command = parts[5]
            jobs.append(CronJob(index=idx, schedule=schedule, command=command, raw=line))
            idx += 1
    return jobs


def add_job(schedule: str, command: str) -> Tuple[bool, str]:
    """Add a new cron job. Returns (success, message)."""
    if not utils.is_linux():
        return False, "Crontab management only available on Linux."
    if not _is_valid_schedule(schedule):
        return False, "Invalid cron schedule expression."
    if security.is_dangerous(command.split()):
        return False, "Command rejected by safety policy."
    existing = utils.run(["crontab", "-l"], timeout=10)
    current = existing.stdout if existing.ok else ""
    new_line = f"{schedule} {command}"
    new_crontab = current.rstrip() + "\n" + new_line + "\n"
    result = utils.run(["crontab", "-"], timeout=10, input_text=new_crontab)
    if result.ok:
        return True, f"Added: {new_line}"
    return False, result.error or result.stderr or "Failed to update crontab."


def remove_job(index: int) -> Tuple[bool, str]:
    """Remove cron job by index. Returns (success, message)."""
    if not utils.is_linux():
        return False, "Crontab management only available on Linux."
    jobs = list_jobs()
    if index < 0 or index >= len(jobs):
        return False, f"No job at index {index}."
    existing = utils.run(["crontab", "-l"], timeout=10)
    if not existing.ok:
        return False, "Could not read crontab."
    lines = existing.stdout.splitlines(keepends=True)
    removed_raw = jobs[index].raw
    new_lines = [l for l in lines if l.rstrip("\r\n") != removed_raw]
    result = utils.run(["crontab", "-"], timeout=10, input_text="".join(new_lines))
    if result.ok:
        return True, f"Removed job #{index}: {jobs[index].command}"
    return False, result.error or result.stderr or "Failed to update crontab."


def list_windows_tasks() -> str:
    """List scheduled tasks on Windows via PowerShell."""
    if not utils.is_windows():
        return "Windows Task Scheduler only available on Windows."
    result = utils.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-ScheduledTask | Select-Object TaskName,State,TaskPath | Format-Table -AutoSize",
        ],
        timeout=20,
    )
    return result.stdout or result.error or "Could not list scheduled tasks."
