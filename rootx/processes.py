"""
rootx.processes
===============
Process Center: list running processes (PID/USER/CPU/RAM/COMMAND), sort by
CPU or RAM, search by name, and kill a process only after explicit
confirmation. A small denylist prevents accidental termination of critical
system processes.

Cross-platform via `psutil`, which exposes the same API on Windows, macOS
and Linux.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from . import utils

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None

# Processes that must never be killed through this tool (checked by name,
# case-insensitive, across all three OSes).
PROTECTED_NAMES = {
    "init", "systemd", "kthreadd", "kernel", "sshd", "xorg",
    "wayland", "dbus-daemon", "networkmanager", "systemd-journald",
    "systemd-logind", "systemd-udevd",
    # macOS
    "launchd", "kernel_task", "windowserver",
    # Windows
    "wininit.exe", "csrss.exe", "smss.exe", "services.exe", "lsass.exe",
    "winlogon.exe", "explorer.exe", "system", "system idle process",
}


@dataclass
class ProcessInfo:
    pid: str
    user: str
    cpu: str
    mem: str
    command: str


def list_processes() -> List[ProcessInfo]:
    """List processes via psutil. Returns an empty list on failure (never crashes)."""
    processes: List[ProcessInfo] = []
    if psutil is None:
        return processes

    try:
        # Prime CPU percent measurement (first call is always 0.0 otherwise).
        for p in psutil.process_iter(["pid"]):
            try:
                p.cpu_percent(interval=None)
            except Exception:
                continue

        for p in psutil.process_iter(["pid", "name", "username", "memory_percent"]):
            try:
                info = p.info
                cpu = p.cpu_percent(interval=None)
                mem = info.get("memory_percent") or 0.0
                processes.append(
                    ProcessInfo(
                        pid=str(info.get("pid", "N/A")),
                        user=str(info.get("username") or "N/A"),
                        cpu=f"{cpu:.1f}",
                        mem=f"{mem:.1f}",
                        command=str(info.get("name") or "N/A"),
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
                continue
    except Exception:
        return []

    return sort_by_cpu(processes)


def sort_by_cpu(processes: List[ProcessInfo]) -> List[ProcessInfo]:
    return sorted(processes, key=lambda p: _safe_float(p.cpu), reverse=True)


def sort_by_mem(processes: List[ProcessInfo]) -> List[ProcessInfo]:
    return sorted(processes, key=lambda p: _safe_float(p.mem), reverse=True)


def search_processes(processes: List[ProcessInfo], query: str) -> List[ProcessInfo]:
    query_lower = query.lower()
    return [p for p in processes if query_lower in p.command.lower() or query_lower in p.pid]


def _safe_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def is_protected(process: ProcessInfo) -> bool:
    if process.pid in ("0", "1", "4"):  # 1=init/launchd, 4=Windows System process
        return True
    name = process.command.strip().lower()
    return any(name == protected or name.startswith(protected) for protected in PROTECTED_NAMES)


def kill_process(pid: str, force: bool = False) -> utils.CommandResult:
    """
    Kill a process by PID. Caller is responsible for confirmation and for
    checking is_protected() beforehand — this function still refuses to
    touch PID 1/0/4 as a last line of defense.
    """
    if pid in ("0", "1", "4"):
        return utils.CommandResult(ok=False, error="Refusing to kill a protected system PID.")

    try:
        pid_int = int(pid)
    except ValueError:
        return utils.CommandResult(ok=False, error=f"Invalid PID: {pid}")

    if psutil is None:
        return utils.CommandResult(ok=False, error="psutil is unavailable; cannot manage processes.")

    try:
        proc = psutil.Process(pid_int)
        if force:
            proc.kill()
        else:
            proc.terminate()
        return utils.CommandResult(ok=True, stdout=f"Signal sent to PID {pid}.")
    except psutil.NoSuchProcess:
        return utils.CommandResult(ok=False, error=f"No such process: {pid}")
    except psutil.AccessDenied:
        return utils.CommandResult(
            ok=False,
            error="Permission denied. Try running the toolkit with elevated privileges.",
        )
    except Exception as exc:
        return utils.CommandResult(ok=False, error=f"Unexpected error: {exc}")
