"""
rootx.update_center
===================
System update and upgrade center.
Linux: apt (primary), dnf/yum/pacman fallback.
Windows: winget.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from . import utils


@dataclass
class UpdateStep:
    name: str
    description: str
    command: List[str]
    requires_sudo: bool = True
    optional: bool = False


@dataclass
class UpdateResult:
    step: str
    ok: bool
    output: str
    error: str = ""


def _detect_linux_backend() -> str:
    """Detect Linux package manager. Returns 'apt'|'dnf'|'yum'|'pacman'|'none'."""
    for pm in ("apt", "dnf", "yum", "pacman"):
        if utils.command_exists(pm):
            return pm
    return "none"


def get_steps() -> List[UpdateStep]:
    """Return the list of update steps for the current OS."""
    steps: List[UpdateStep] = []
    if utils.is_linux():
        backend = _detect_linux_backend()
        if backend == "apt":
            steps = [
                UpdateStep("update", "Refresh package index", ["apt", "update"], True),
                UpdateStep("upgrade", "Upgrade all packages", ["apt", "upgrade", "-y"], True),
                UpdateStep("autoremove", "Remove unused packages", ["apt", "autoremove", "-y"], True),
                UpdateStep("clean", "Clean package cache", ["apt", "clean"], True),
            ]
        elif backend == "dnf":
            steps = [
                UpdateStep("upgrade", "Upgrade all packages", ["dnf", "upgrade", "-y"], True),
                UpdateStep("autoremove", "Remove unused packages", ["dnf", "autoremove", "-y"], True, optional=True),
            ]
        elif backend == "yum":
            steps = [
                UpdateStep("update", "Update all packages", ["yum", "update", "-y"], True),
            ]
        elif backend == "pacman":
            steps = [
                UpdateStep("sync", "Sync and upgrade", ["pacman", "-Syu", "--noconfirm"], True),
            ]
    elif utils.is_windows():
        if utils.command_exists("winget"):
            steps = [
                UpdateStep("source update", "Refresh winget sources", ["winget", "source", "update"], False),
                UpdateStep("upgrade --all", "Upgrade all packages", ["winget", "upgrade", "--all", "--include-unknown"], False),
            ]
    return steps


def run_step(step: UpdateStep) -> UpdateResult:
    """Execute a single update step with sudo prefix where needed."""
    prefix = utils.sudo_prefix() if step.requires_sudo else []
    cmd = prefix + step.command
    result = utils.run(cmd, timeout=600)
    return UpdateResult(
        step=step.name, ok=result.ok,
        output=result.stdout, error=result.error or result.stderr
    )


def run_all(progress_callback: Optional[Callable[[str], None]] = None) -> List[UpdateResult]:
    """Run all update steps. progress_callback called with step name before each step."""
    steps = get_steps()
    results: List[UpdateResult] = []
    for step in steps:
        if progress_callback:
            progress_callback(step.name)
        result = run_step(step)
        results.append(result)
    return results


def cleanup_only() -> List[UpdateResult]:
    """Run only cleanup steps (autoremove, clean)."""
    steps = [s for s in get_steps() if s.name in ("autoremove", "clean")]
    return [run_step(s) for s in steps]


def estimate_upgradable() -> str:
    """Show how many packages can be upgraded."""
    if utils.is_linux():
        backend = _detect_linux_backend()
        if backend == "apt":
            result = utils.run(["apt", "list", "--upgradable"], timeout=30)
            lines = [l for l in result.stdout.splitlines() if l.strip() and "Listing..." not in l]
            return f"{len(lines)} package(s) upgradable."
        elif backend in ("dnf", "yum"):
            result = utils.run([backend, "check-update"], timeout=30)
            lines = [l for l in result.stdout.splitlines() if l.strip() and not l.startswith("Last")]
            return f"{len(lines)} package(s) upgradable."
    elif utils.is_windows():
        if utils.command_exists("winget"):
            result = utils.run(["winget", "upgrade"], timeout=30)
            lines = [l for l in result.stdout.splitlines() if l.strip()]
            return result.stdout[:500] or "Could not determine upgradable packages."
    return "Could not determine upgradable packages."
