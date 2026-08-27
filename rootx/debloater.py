"""
rootx.debloater
===============
Windows / Linux Debloater & Telemetry Stripper.

Silver tier: disable tracking services
Gold tier: advanced (registry tweaks on Windows, kernel params on Linux)
"""
from __future__ import annotations

import platform
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class DebloatResult:
    success: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)


# ─── Windows ──────────────────────────────────────────────────────────────────

WINDOWS_TELEMETRY_SERVICES = [
    {"name": "DiagTrack",          "display": "Connected User Experiences and Telemetry"},
    {"name": "dmwappushservice",   "display": "WAP Push Message Routing Service"},
    {"name": "WerSvc",             "display": "Windows Error Reporting Service"},
    {"name": "PcaSvc",             "display": "Program Compatibility Assistant Service"},
    {"name": "RemoteRegistry",     "display": "Remote Registry"},
    {"name": "CDPSvc",             "display": "Connected Devices Platform Service"},
    {"name": "MapsBroker",         "display": "Downloaded Maps Manager"},
    {"name": "RetailDemo",         "display": "Retail Demo Service"},
    {"name": "SysMain",            "display": "Superfetch (SysMain)"},
    {"name": "WSearch",            "display": "Windows Search (indexing)"},
]

WINDOWS_REGISTRY_TWEAKS = [
    {
        "name": "Disable Cortana",
        "key": r"HKLM\SOFTWARE\Policies\Microsoft\Windows\Windows Search",
        "value": "AllowCortana",
        "type": "REG_DWORD",
        "data": "0",
    },
    {
        "name": "Disable Bing Search in Start Menu",
        "key": r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Search",
        "value": "BingSearchEnabled",
        "type": "REG_DWORD",
        "data": "0",
    },
    {
        "name": "Disable Telemetry (set to Security only)",
        "key": r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection",
        "value": "AllowTelemetry",
        "type": "REG_DWORD",
        "data": "0",
    },
    {
        "name": "Disable Activity History",
        "key": r"HKLM\SOFTWARE\Policies\Microsoft\Windows\System",
        "value": "PublishUserActivities",
        "type": "REG_DWORD",
        "data": "0",
    },
    {
        "name": "Disable Advertising ID",
        "key": r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
        "value": "Enabled",
        "type": "REG_DWORD",
        "data": "0",
    },
    {
        "name": "Disable Location Tracking",
        "key": r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Sensor\Overrides\{BFA794E4-F964-4FDB-90F6-51056BFE4B44}",
        "value": "SensorPermissionState",
        "type": "REG_DWORD",
        "data": "0",
    },
    {
        "name": "Disable Start Menu Web Search",
        "key": r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Search",
        "value": "AllowSearchToUseLocation",
        "type": "REG_DWORD",
        "data": "0",
    },
]


def _run(cmd: List[str]) -> bool:
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        return result.returncode == 0
    except Exception:
        return False


def disable_windows_service(svc_name: str) -> bool:
    stopped = _run(["sc", "stop", svc_name])
    disabled = _run(["sc", "config", svc_name, "start=", "disabled"])
    return disabled


def apply_registry_tweak(tweak: Dict) -> bool:
    cmd = [
        "reg", "add", tweak["key"],
        "/v", tweak["value"],
        "/t", tweak["type"],
        "/d", tweak["data"],
        "/f",
    ]
    return _run(cmd)


def run_windows_debloat(tier: str = "silver") -> DebloatResult:
    result = DebloatResult()

    # Silver: disable telemetry services
    for svc in WINDOWS_TELEMETRY_SERVICES:
        ok = disable_windows_service(svc["name"])
        if ok:
            result.success.append(f"Service disabled: {svc['display']}")
        else:
            result.failed.append(f"Service: {svc['display']}")

    # Gold: apply registry tweaks
    if tier == "gold":
        for tweak in WINDOWS_REGISTRY_TWEAKS:
            ok = apply_registry_tweak(tweak)
            if ok:
                result.success.append(f"Registry: {tweak['name']}")
            else:
                result.failed.append(f"Registry: {tweak['name']}")

    return result


# ─── Linux ────────────────────────────────────────────────────────────────────

LINUX_BLOAT_SERVICES = [
    {"name": "snapd",             "display": "Snap daemon"},
    {"name": "apport",            "display": "Apport crash reporter"},
    {"name": "whoopsie",          "display": "Whoopsie (Ubuntu error reporting)"},
    {"name": "avahi-daemon",      "display": "Avahi mDNS/DNS-SD daemon"},
    {"name": "cups",              "display": "CUPS printing service"},
    {"name": "popularity-contest","display": "Popularity Contest"},
    {"name": "motd-news",         "display": "MOTD news service"},
    {"name": "apt-daily",         "display": "APT daily auto-update timer"},
    {"name": "apt-daily-upgrade", "display": "APT daily upgrade timer"},
]

LINUX_ADVANCED_TWEAKS = [
    {
        "name": "Disable kernel pointer exposure",
        "cmd": ["sysctl", "-w", "kernel.kptr_restrict=2"],
    },
    {
        "name": "Disable magic SysRq key",
        "cmd": ["sysctl", "-w", "kernel.sysrq=0"],
    },
    {
        "name": "Disable core dumps",
        "cmd": ["sysctl", "-w", "kernel.core_pattern=|/bin/false"],
    },
]


def disable_linux_service(svc_name: str) -> bool:
    return _run(["systemctl", "disable", "--now", svc_name])


def run_linux_debloat(tier: str = "silver") -> DebloatResult:
    result = DebloatResult()

    for svc in LINUX_BLOAT_SERVICES:
        ok = disable_linux_service(svc["name"])
        if ok:
            result.success.append(f"Service disabled: {svc['display']}")
        else:
            result.skipped.append(f"Service not found/running: {svc['display']}")

    if tier == "gold":
        for tweak in LINUX_ADVANCED_TWEAKS:
            ok = _run(tweak["cmd"])
            if ok:
                result.success.append(f"Kernel: {tweak['name']}")
            else:
                result.failed.append(f"Kernel: {tweak['name']}")

    return result


# ─── Public API ───────────────────────────────────────────────────────────────

def run_debloat(tier: str = "silver") -> DebloatResult:
    """Run debloat for the current platform."""
    system = platform.system()
    if system == "Windows":
        return run_windows_debloat(tier)
    elif system == "Linux":
        return run_linux_debloat(tier)
    else:
        r = DebloatResult()
        r.skipped.append(f"Platform '{system}' not supported.")
        return r


def get_windows_telemetry_services() -> List[Dict]:
    return WINDOWS_TELEMETRY_SERVICES


def get_windows_registry_tweaks() -> List[Dict]:
    return WINDOWS_REGISTRY_TWEAKS


def get_linux_bloat_services() -> List[Dict]:
    return LINUX_BLOAT_SERVICES
