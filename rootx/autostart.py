"""
rootx.autostart
===============
Persistence & Auto-start Inspector.
Checks all autostart locations on Windows and Linux.
"""
from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class AutostartEntry:
    source: str       # e.g. "Registry: HKCU Run", "Systemd user", "~/.config/autostart"
    name: str
    command: str
    suspicious: bool = False


_SAFE_PREFIXES = [
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\Windows",
    "/usr/",
    "/bin/",
    "/sbin/",
    "/lib/",
    "/opt/",
]

_SUSPICIOUS_PATTERNS = [
    "\\temp\\", "\\tmp\\", "/tmp/",
    "appdata\\local\\temp",
    "%temp%",
    ".vbs", ".bat", ".cmd", ".ps1", ".py",
    "powershell -", "cmd /c", "wscript",
    "curl ", "wget ",
]


def _is_suspicious(command: str) -> bool:
    cmd_lower = command.lower().strip()
    for pattern in _SUSPICIOUS_PATTERNS:
        if pattern in cmd_lower:
            return True
    # Check if executable exists
    parts = cmd_lower.split()
    if parts:
        exe = parts[0].strip('"').strip("'")
        if exe and not exe.startswith("/") and not os.path.exists(exe):
            # Might be a relative path or missing file
            if not any(exe.startswith(p.lower()) for p in _SAFE_PREFIXES):
                pass  # Don't auto-flag just for not existing — too many false positives
    return False


def _run_output(cmd: List[str], encoding: str = "utf-8") -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                encoding=encoding, errors="replace", timeout=15)
        return result.stdout or ""
    except Exception:
        return ""


# ─── Windows ──────────────────────────────────────────────────────────────────

def get_windows_registry_run() -> List[AutostartEntry]:
    entries = []
    reg_keys = [
        (r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "Registry: HKCU Run"),
        (r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "Registry: HKCU RunOnce"),
        (r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "Registry: HKLM Run"),
        (r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "Registry: HKLM RunOnce"),
        (r"HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "Registry: HKLM Run (x86)"),
    ]
    for key, source in reg_keys:
        output = _run_output(["reg", "query", key])
        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("HKEY"):
                continue
            parts = line.split(None, 2)
            if len(parts) >= 3 and parts[1].upper() in ("REG_SZ", "REG_EXPAND_SZ"):
                name = parts[0]
                cmd = parts[2]
                entries.append(AutostartEntry(
                    source=source,
                    name=name,
                    command=cmd,
                    suspicious=_is_suspicious(cmd),
                ))
    return entries


def get_windows_startup_folder() -> List[AutostartEntry]:
    entries = []
    folders = []
    user_startup = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    common_startup = Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs/Startup")
    for folder, source in [(user_startup, "Startup Folder (User)"), (common_startup, "Startup Folder (All Users)")]:
        if folder.exists():
            for item in folder.iterdir():
                entries.append(AutostartEntry(
                    source=source,
                    name=item.name,
                    command=str(item),
                    suspicious=_is_suspicious(str(item)),
                ))
    return entries


def get_windows_scheduled_tasks() -> List[AutostartEntry]:
    entries = []
    output = _run_output(["schtasks", "/query", "/fo", "LIST", "/v"])
    current: dict = {}
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("TaskName:"):
            current["name"] = line.split(":", 1)[-1].strip()
        elif line.startswith("Task To Run:"):
            current["cmd"] = line.split(":", 1)[-1].strip()
        elif line.startswith("Status:"):
            current["status"] = line.split(":", 1)[-1].strip()
            if current.get("name") and current.get("cmd"):
                cmd = current["cmd"]
                name = current["name"]
                if cmd not in ("N/A", "") and not name.startswith("\\Microsoft\\"):
                    entries.append(AutostartEntry(
                        source="Scheduled Task",
                        name=name.split("\\")[-1],
                        command=cmd,
                        suspicious=_is_suspicious(cmd),
                    ))
            current = {}
    return entries


# ─── Linux ────────────────────────────────────────────────────────────────────

def get_linux_systemd_user() -> List[AutostartEntry]:
    entries = []
    output = _run_output(["systemctl", "list-unit-files", "--user", "--state=enabled", "--no-pager"])
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("UNIT") or line.startswith("Legend"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "enabled":
            name = parts[0]
            entries.append(AutostartEntry(
                source="Systemd User",
                name=name,
                command=name,
                suspicious=False,
            ))
    return entries


def get_linux_xdg_autostart() -> List[AutostartEntry]:
    entries = []
    dirs = [
        Path.home() / ".config" / "autostart",
        Path("/etc/xdg/autostart"),
    ]
    for d in dirs:
        if d.exists():
            for f in d.glob("*.desktop"):
                try:
                    content = f.read_text(errors="replace")
                    name = f.stem
                    exec_cmd = ""
                    for line in content.splitlines():
                        if line.startswith("Name="):
                            name = line[5:].strip()
                        elif line.startswith("Exec="):
                            exec_cmd = line[5:].strip()
                    entries.append(AutostartEntry(
                        source=f"XDG Autostart ({d})",
                        name=name,
                        command=exec_cmd or str(f),
                        suspicious=_is_suspicious(exec_cmd),
                    ))
                except Exception:
                    pass
    return entries


def get_linux_shell_rc() -> List[AutostartEntry]:
    entries = []
    rc_files = [
        Path.home() / ".bashrc",
        Path.home() / ".bash_profile",
        Path.home() / ".profile",
        Path.home() / ".zshrc",
        Path.home() / ".zprofile",
    ]
    suspicious_rc_cmds = ["curl", "wget", "nc ", "ncat", "bash -i", "python", "perl", "ruby"]
    for rc in rc_files:
        if rc.exists():
            try:
                lines = rc.read_text(errors="replace").splitlines()
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        for s in suspicious_rc_cmds:
                            if s in stripped.lower():
                                entries.append(AutostartEntry(
                                    source=f"Shell RC: {rc.name}",
                                    name=f"Line {i}",
                                    command=stripped,
                                    suspicious=True,
                                ))
                                break
            except Exception:
                pass
    return entries


def get_linux_initd() -> List[AutostartEntry]:
    entries = []
    initd = Path("/etc/init.d")
    if initd.exists():
        for item in initd.iterdir():
            if item.is_file():
                entries.append(AutostartEntry(
                    source="SysV init.d",
                    name=item.name,
                    command=str(item),
                    suspicious=False,
                ))
    return entries


# ─── Removal ──────────────────────────────────────────────────────────────────

def remove_windows_run_entry(name: str, hive: str = "HKCU") -> bool:
    key = rf"{hive}\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
    try:
        result = subprocess.run(
            ["reg", "delete", key, "/v", name, "/f"],
            capture_output=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def remove_linux_xdg_entry(filename: str) -> bool:
    target = Path.home() / ".config" / "autostart" / filename
    if not target.suffix:
        target = target.with_suffix(".desktop")
    try:
        if target.exists():
            target.unlink()
            return True
        return False
    except Exception:
        return False


# ─── Public API ───────────────────────────────────────────────────────────────

def scan_all() -> List[AutostartEntry]:
    """Scan all autostart locations for the current platform."""
    system = platform.system()
    if system == "Windows":
        entries = []
        entries.extend(get_windows_registry_run())
        entries.extend(get_windows_startup_folder())
        entries.extend(get_windows_scheduled_tasks())
        return entries
    elif system == "Linux":
        entries = []
        entries.extend(get_linux_systemd_user())
        entries.extend(get_linux_xdg_autostart())
        entries.extend(get_linux_shell_rc())
        entries.extend(get_linux_initd())
        return entries
    else:
        return []
