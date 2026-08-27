"""
rootx.services
==============
Service Manager: on Linux wraps `systemctl`, on Windows wraps the native
Service Control Manager via PowerShell (Get-Service / Start-Service / ...),
on macOS wraps `launchctl`. Gracefully degrades to "unavailable" instead of
crashing when the platform's service layer can't be reached.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from . import utils


@dataclass
class ServiceInfo:
    name: str
    load: str = "N/A"
    active: str = "N/A"
    sub: str = "N/A"
    description: str = ""


def service_manager_available() -> bool:
    if utils.is_linux():
        return utils.command_exists("systemctl")
    if utils.is_windows():
        return utils.command_exists("powershell") or utils.command_exists("sc")
    if utils.is_macos():
        return utils.command_exists("launchctl")
    return False


# Backwards-compatible alias used by older call sites / menus.
def systemd_available() -> bool:
    return service_manager_available()


def list_services(state: str = "running") -> List[ServiceInfo]:
    """
    state: 'running', 'failed', or 'stopped' (best-effort mapping per OS;
    'failed' has no real equivalent on Windows/macOS and returns []).
    """
    if not service_manager_available():
        return []

    if utils.is_linux():
        return _list_services_linux(state)
    if utils.is_windows():
        return _list_services_windows(state)
    if utils.is_macos():
        return _list_services_macos(state)
    return []


def _list_services_linux(state: str) -> List[ServiceInfo]:
    if state == "failed":
        args = ["systemctl", "list-units", "--type=service", "--state=failed", "--no-legend", "--no-pager"]
    elif state == "stopped":
        args = ["systemctl", "list-units", "--type=service", "--state=inactive", "--no-legend", "--no-pager"]
    else:
        args = ["systemctl", "list-units", "--type=service", "--state=running", "--no-legend", "--no-pager"]

    result = utils.run(args, timeout=10)
    services: List[ServiceInfo] = []
    if not result.ok or not result.stdout:
        return services

    for line in result.stdout.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue
        name, load, active, sub = parts[0], parts[1], parts[2], parts[3]
        description = parts[4] if len(parts) > 4 else ""
        services.append(ServiceInfo(name=name, load=load, active=active, sub=sub, description=description))
    return services


def _list_services_windows(state: str) -> List[ServiceInfo]:
    if state == "failed":
        return []  # Windows has no direct "failed" service concept
    status_filter = "Stopped" if state == "stopped" else "Running"
    ps_cmd = (
        f"Get-Service | Where-Object {{$_.Status -eq '{status_filter}'}} | "
        "Select-Object -First 100 Name,Status,DisplayName | "
        "ForEach-Object {{ \"$($_.Name)|$($_.Status)|$($_.DisplayName)\" }}"
    )
    result = utils.run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=15)
    services: List[ServiceInfo] = []
    if not result.ok or not result.stdout:
        return services
    for line in result.stdout.splitlines():
        parts = line.split("|", 2)
        if len(parts) < 2:
            continue
        name = parts[0].strip()
        status = parts[1].strip()
        desc = parts[2].strip() if len(parts) > 2 else ""
        services.append(ServiceInfo(name=name, load="N/A", active=status, sub=status, description=desc))
    return services


def _list_services_macos(state: str) -> List[ServiceInfo]:
    if state == "failed":
        return []  # launchctl doesn't expose a clean "failed" state
    result = utils.run(["launchctl", "list"], timeout=10)
    services: List[ServiceInfo] = []
    if not result.ok or not result.stdout:
        return services
    lines = result.stdout.splitlines()[1:]  # skip header
    for line in lines:
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid, exit_status, label = parts[0], parts[1], parts[2]
        running = pid != "-"
        if state == "stopped" and running:
            continue
        if state == "running" and not running:
            continue
        active = "running" if running else "stopped"
        services.append(ServiceInfo(name=label, load="N/A", active=active, sub=exit_status))
    return services


def get_failed_services() -> List[ServiceInfo]:
    return list_services(state="failed")


def service_status(name: str) -> utils.CommandResult:
    if utils.is_linux():
        return utils.run(["systemctl", "status", name, "--no-pager"], timeout=10)
    if utils.is_windows():
        return utils.run(
            ["powershell", "-NoProfile", "-Command", f"Get-Service -Name '{name}' | Format-List *"],
            timeout=10,
        )
    if utils.is_macos():
        return utils.run(["launchctl", "list", name], timeout=10)
    return utils.CommandResult(ok=False, error="Unsupported platform.")


def service_logs(name: str, lines: int = 30) -> utils.CommandResult:
    if utils.is_linux():
        return utils.run(["journalctl", "-u", name, "-n", str(lines), "--no-pager"], timeout=10)
    if utils.is_windows():
        ps_cmd = (
            f"Get-EventLog -LogName Application -Source '{name}' -Newest {lines} | "
            "Format-Table TimeGenerated,EntryType,Message -Wrap"
        )
        return utils.run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=15)
    return utils.CommandResult(ok=False, error="Log viewing is not available for this service on macOS.")


def _control(action: str, name: str) -> utils.CommandResult:
    """Internal helper for start/stop/restart/enable/disable, per OS."""
    if utils.is_linux():
        prefix = utils.sudo_prefix()
        return utils.run(prefix + ["systemctl", action, name], timeout=20)

    if utils.is_windows():
        mapping = {
            "start": f"Start-Service -Name '{name}'",
            "stop": f"Stop-Service -Name '{name}' -Force",
            "restart": f"Restart-Service -Name '{name}' -Force",
            "enable": f"Set-Service -Name '{name}' -StartupType Automatic",
            "disable": f"Set-Service -Name '{name}' -StartupType Disabled",
        }
        ps_cmd = mapping.get(action)
        if not ps_cmd:
            return utils.CommandResult(ok=False, error=f"Unsupported action: {action}")
        return utils.run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=30)

    if utils.is_macos():
        mapping = {
            "start": ["launchctl", "start", name],
            "stop": ["launchctl", "stop", name],
            "restart": ["launchctl", "kickstart", "-k", name],
        }
        cmd = mapping.get(action)
        if not cmd:
            return utils.CommandResult(
                ok=False,
                error="enable/disable are not supported for launchd services from here.",
            )
        return utils.run(cmd, timeout=20)

    return utils.CommandResult(ok=False, error="Unsupported platform.")


def start_service(name: str) -> utils.CommandResult:
    return _control("start", name)


def stop_service(name: str) -> utils.CommandResult:
    return _control("stop", name)


def restart_service(name: str) -> utils.CommandResult:
    return _control("restart", name)


def enable_service(name: str) -> utils.CommandResult:
    return _control("enable", name)


def disable_service(name: str) -> utils.CommandResult:
    return _control("disable", name)
