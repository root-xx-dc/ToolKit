"""
rootx.doctor
============
ROOT//X DOCTOR — the flagship diagnostic module.

`run_diagnostics()` performs a purely read-only audit of the system
(no scanning, no mutation) and returns a structured DoctorReport.
`get_safe_fixes()` returns a registry of safe, reversible-ish remediation
actions appropriate for the current OS; every one of them still requires
explicit user confirmation before it is ever executed — this module never
runs them on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from . import network, packages, services, storage, system, utils


@dataclass
class DoctorFinding:
    category: str
    severity: str   # "ok", "warning", "critical"
    message: str


@dataclass
class DoctorReport:
    system_info: system.SystemInfo
    storage_result: dict
    network_result: network.NetworkDoctorResult
    failed_services: List[services.ServiceInfo]
    package_manager: Optional[str]
    findings: List[DoctorFinding] = field(default_factory=list)

    @property
    def warnings(self) -> List[DoctorFinding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def criticals(self) -> List[DoctorFinding]:
        return [f for f in self.findings if f.severity == "critical"]

    @property
    def problem_count(self) -> int:
        return len(self.warnings) + len(self.criticals)


def _required_commands() -> List[str]:
    if utils.is_windows():
        return ["ping", "powershell"]
    if utils.is_macos():
        return ["ping", "curl", "git"]
    return ["ip", "ping", "df", "curl", "git"]


def _check_required_commands() -> List[DoctorFinding]:
    required = _required_commands()
    findings = []
    missing = [cmd for cmd in required if not utils.command_exists(cmd)]
    if missing:
        findings.append(
            DoctorFinding(
                category="Required Commands",
                severity="warning",
                message=f"Missing commands: {', '.join(missing)}",
            )
        )
    return findings


def _check_logs(max_lines: int = 10) -> List[DoctorFinding]:
    """Read only a limited number of recent critical log entries (Linux/journald only)."""
    findings: List[DoctorFinding] = []
    if not utils.is_linux() or not utils.command_exists("journalctl"):
        return findings
    result = utils.run(
        ["journalctl", "-p", "3", "-n", str(max_lines), "--no-pager"],
        timeout=10,
    )
    if result.ok and result.stdout.strip():
        line_count = len(result.stdout.strip().splitlines())
        findings.append(
            DoctorFinding(
                category="Logs",
                severity="warning",
                message=f"{line_count} recent critical log entries found (see report for detail).",
            )
        )
    return findings


def run_diagnostics() -> DoctorReport:
    """Run the full safe, read-only Doctor audit."""
    sys_info = system.collect()
    storage_result = storage.diagnose()
    net_result = network.network_doctor()
    failed = services.get_failed_services() if services.service_manager_available() else []
    backend = packages.get_backend()

    findings: List[DoctorFinding] = []

    # Storage
    for mount in storage_result["criticals"]:
        findings.append(
            DoctorFinding(
                "Storage", "critical",
                f"{mount.mount_point} volume is {mount.percent}% full.",
            )
        )
    for mount in storage_result["warnings"]:
        findings.append(
            DoctorFinding(
                "Storage", "warning",
                f"{mount.mount_point} volume is {mount.percent}% full.",
            )
        )

    # Network
    if net_result.suggestion:
        severity = "critical" if net_result.internet_ok is False and net_result.gateway_ok is False else "warning"
        findings.append(DoctorFinding("Network", severity, net_result.suggestion))

    # Failed / stopped services (Linux systemd only gets a strict "failed" state)
    if failed:
        findings.append(
            DoctorFinding(
                "Services", "warning",
                f"{len(failed)} service(s) failed: {', '.join(s.name for s in failed[:5])}",
            )
        )

    # Package manager
    if backend is None:
        findings.append(
            DoctorFinding("Package Manager", "warning", "No supported package manager detected.")
        )

    findings.extend(_check_required_commands())
    findings.extend(_check_logs())

    return DoctorReport(
        system_info=sys_info,
        storage_result=storage_result,
        network_result=net_result,
        failed_services=failed,
        package_manager=backend.name if backend else None,
        findings=findings,
    )


# ---------------------------------------------------------------------------
# Safe fixes registry
# ---------------------------------------------------------------------------


@dataclass
class SafeFix:
    key: str
    problem: str
    command: List[str]
    description: str
    requires_sudo: bool = True

    def build_display_command(self) -> str:
        prefix = utils.sudo_prefix() if self.requires_sudo else []
        return " ".join(prefix + self.command)

    def execute(self) -> utils.CommandResult:
        prefix = utils.sudo_prefix() if self.requires_sudo else []
        return utils.run(prefix + self.command, timeout=180)


def get_safe_fixes(report: DoctorReport) -> List[SafeFix]:
    """Build the list of applicable safe fixes based on the current report and OS."""
    fixes: List[SafeFix] = []

    if report.package_manager == "apt":
        fixes.append(SafeFix(
            key="dpkg_configure",
            problem="APT package database may be inconsistent.",
            command=["dpkg", "--configure", "-a"],
            description="This attempts to finish configuring previously interrupted packages.",
        ))
        fixes.append(SafeFix(
            key="apt_fix_broken",
            problem="APT may have broken/unmet dependencies.",
            command=["apt", "--fix-broken", "install", "-y"],
            description="Attempts to resolve broken dependency chains via apt.",
        ))
        fixes.append(SafeFix(
            key="apt_clean",
            problem="APT package cache may be using excessive disk space.",
            command=["apt", "clean"],
            description="Clears the local package cache in /var/cache/apt without removing installed packages.",
        ))
    elif report.package_manager == "pacman":
        fixes.append(SafeFix(
            key="pacman_clean_cache",
            problem="Pacman package cache may be using excessive disk space.",
            command=["pacman", "-Sc", "--noconfirm"],
            description="Removes cached packages that are no longer installed.",
        ))
    elif report.package_manager in ("dnf", "yum"):
        fixes.append(SafeFix(
            key="dnf_clean",
            problem="DNF/YUM package cache may be using excessive disk space.",
            command=[report.package_manager, "clean", "all"],
            description="Clears cached package metadata and packages.",
        ))
    elif report.package_manager == "brew":
        fixes.append(SafeFix(
            key="brew_cleanup",
            problem="Homebrew's download cache may be using excessive disk space.",
            command=["brew", "cleanup"],
            description="Removes old versions and cached downloads no longer needed by Homebrew.",
            requires_sudo=False,
        ))
    elif report.package_manager == "winget":
        fixes.append(SafeFix(
            key="winget_source_update",
            problem="winget's local source index may be stale.",
            command=["winget", "source", "update"],
            description="Refreshes winget's package source metadata.",
            requires_sudo=False,
        ))

    if report.failed_services:
        for svc in report.failed_services[:5]:
            if utils.is_linux():
                fixes.append(SafeFix(
                    key=f"restart_{svc.name}",
                    problem=f"Service '{svc.name}' has failed.",
                    command=["systemctl", "restart", svc.name],
                    description=f"Attempts to restart the failed service '{svc.name}'.",
                ))

    if report.network_result.dns_ok is False and utils.is_linux():
        fixes.append(SafeFix(
            key="restart_networkmanager",
            problem="DNS resolution is failing.",
            command=["systemctl", "restart", "NetworkManager"],
            description="Restarts NetworkManager, which often resolves transient DNS issues.",
        ))

    return fixes
