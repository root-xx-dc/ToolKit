"""
rootx.packages
==============
Universal Package Engine.

Defines a common PackageManagerBackend interface and one concrete
implementation per native package manager — six Linux backends plus
Homebrew (macOS) and winget/Chocolatey (Windows). `get_backend()`
auto-detects which one is available on the current system. Every mutating
operation (install / remove / update) returns the exact command that WOULD
run; execution is a separate, explicit step so the CLI layer can always
show the command and ask for confirmation first.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from . import utils


@dataclass
class PackagePlan:
    """Describes an action without executing it."""

    action: str          # "install", "remove", "update", "upgrade", "search"
    package_manager: str
    command: List[str]
    requires_sudo: bool = True

    @property
    def display_command(self) -> str:
        prefix = utils.sudo_prefix() if self.requires_sudo else []
        return " ".join(prefix + self.command)


class PackageManagerBackend(ABC):
    name: str = "base"
    binary: str = ""

    def is_available(self) -> bool:
        return utils.command_exists(self.binary)

    @abstractmethod
    def install_plan(self, package: str) -> PackagePlan: ...

    @abstractmethod
    def remove_plan(self, package: str) -> PackagePlan: ...

    @abstractmethod
    def update_plan(self) -> PackagePlan: ...

    @abstractmethod
    def upgrade_plan(self) -> PackagePlan: ...

    @abstractmethod
    def search_plan(self, query: str) -> PackagePlan: ...

    @abstractmethod
    def is_installed(self, package: str) -> bool: ...

    def execute(self, plan: PackagePlan) -> utils.CommandResult:
        """Execute a previously built plan. Caller must confirm with the user first."""
        prefix = utils.sudo_prefix() if plan.requires_sudo else []
        return utils.run(prefix + plan.command, timeout=300)

    def search(self, query: str) -> utils.CommandResult:
        """Search is read-only, safe to execute directly."""
        plan = self.search_plan(query)
        return utils.run(plan.command, timeout=30)


# ---------------------------------------------------------------------------
# Linux backends
# ---------------------------------------------------------------------------


class AptManager(PackageManagerBackend):
    name = "apt"
    binary = "apt"

    def install_plan(self, package: str) -> PackagePlan:
        return PackagePlan("install", self.name, ["apt", "install", "-y", package])

    def remove_plan(self, package: str) -> PackagePlan:
        return PackagePlan("remove", self.name, ["apt", "remove", "-y", package])

    def update_plan(self) -> PackagePlan:
        return PackagePlan("update", self.name, ["apt", "update"])

    def upgrade_plan(self) -> PackagePlan:
        return PackagePlan("upgrade", self.name, ["apt", "upgrade", "-y"])

    def search_plan(self, query: str) -> PackagePlan:
        return PackagePlan("search", self.name, ["apt-cache", "search", query], requires_sudo=False)

    def is_installed(self, package: str) -> bool:
        result = utils.run(["dpkg", "-s", package], timeout=5)
        return result.ok


class PacmanManager(PackageManagerBackend):
    name = "pacman"
    binary = "pacman"

    def install_plan(self, package: str) -> PackagePlan:
        return PackagePlan("install", self.name, ["pacman", "-S", "--noconfirm", package])

    def remove_plan(self, package: str) -> PackagePlan:
        return PackagePlan("remove", self.name, ["pacman", "-R", "--noconfirm", package])

    def update_plan(self) -> PackagePlan:
        return PackagePlan("update", self.name, ["pacman", "-Sy"])

    def upgrade_plan(self) -> PackagePlan:
        return PackagePlan("upgrade", self.name, ["pacman", "-Syu", "--noconfirm"])

    def search_plan(self, query: str) -> PackagePlan:
        return PackagePlan("search", self.name, ["pacman", "-Ss", query], requires_sudo=False)

    def is_installed(self, package: str) -> bool:
        result = utils.run(["pacman", "-Q", package], timeout=5)
        return result.ok


class DnfManager(PackageManagerBackend):
    name = "dnf"
    binary = "dnf"

    def install_plan(self, package: str) -> PackagePlan:
        return PackagePlan("install", self.name, ["dnf", "install", "-y", package])

    def remove_plan(self, package: str) -> PackagePlan:
        return PackagePlan("remove", self.name, ["dnf", "remove", "-y", package])

    def update_plan(self) -> PackagePlan:
        return PackagePlan("update", self.name, ["dnf", "check-update"])

    def upgrade_plan(self) -> PackagePlan:
        return PackagePlan("upgrade", self.name, ["dnf", "upgrade", "-y"])

    def search_plan(self, query: str) -> PackagePlan:
        return PackagePlan("search", self.name, ["dnf", "search", query], requires_sudo=False)

    def is_installed(self, package: str) -> bool:
        result = utils.run(["rpm", "-q", package], timeout=5)
        return result.ok


class YumManager(PackageManagerBackend):
    name = "yum"
    binary = "yum"

    def install_plan(self, package: str) -> PackagePlan:
        return PackagePlan("install", self.name, ["yum", "install", "-y", package])

    def remove_plan(self, package: str) -> PackagePlan:
        return PackagePlan("remove", self.name, ["yum", "remove", "-y", package])

    def update_plan(self) -> PackagePlan:
        return PackagePlan("update", self.name, ["yum", "check-update"])

    def upgrade_plan(self) -> PackagePlan:
        return PackagePlan("upgrade", self.name, ["yum", "update", "-y"])

    def search_plan(self, query: str) -> PackagePlan:
        return PackagePlan("search", self.name, ["yum", "search", query], requires_sudo=False)

    def is_installed(self, package: str) -> bool:
        result = utils.run(["rpm", "-q", package], timeout=5)
        return result.ok


class ZypperManager(PackageManagerBackend):
    name = "zypper"
    binary = "zypper"

    def install_plan(self, package: str) -> PackagePlan:
        return PackagePlan("install", self.name, ["zypper", "install", "-y", package])

    def remove_plan(self, package: str) -> PackagePlan:
        return PackagePlan("remove", self.name, ["zypper", "remove", "-y", package])

    def update_plan(self) -> PackagePlan:
        return PackagePlan("update", self.name, ["zypper", "refresh"])

    def upgrade_plan(self) -> PackagePlan:
        return PackagePlan("upgrade", self.name, ["zypper", "update", "-y"])

    def search_plan(self, query: str) -> PackagePlan:
        return PackagePlan("search", self.name, ["zypper", "search", query], requires_sudo=False)

    def is_installed(self, package: str) -> bool:
        result = utils.run(["rpm", "-q", package], timeout=5)
        return result.ok


class ApkManager(PackageManagerBackend):
    name = "apk"
    binary = "apk"

    def install_plan(self, package: str) -> PackagePlan:
        return PackagePlan("install", self.name, ["apk", "add", package])

    def remove_plan(self, package: str) -> PackagePlan:
        return PackagePlan("remove", self.name, ["apk", "del", package])

    def update_plan(self) -> PackagePlan:
        return PackagePlan("update", self.name, ["apk", "update"])

    def upgrade_plan(self) -> PackagePlan:
        return PackagePlan("upgrade", self.name, ["apk", "upgrade"])

    def search_plan(self, query: str) -> PackagePlan:
        return PackagePlan("search", self.name, ["apk", "search", query], requires_sudo=False)

    def is_installed(self, package: str) -> bool:
        result = utils.run(["apk", "info", "-e", package], timeout=5)
        return result.ok and bool(result.stdout)


# ---------------------------------------------------------------------------
# macOS backend
# ---------------------------------------------------------------------------


class BrewManager(PackageManagerBackend):
    name = "brew"
    binary = "brew"

    def install_plan(self, package: str) -> PackagePlan:
        return PackagePlan("install", self.name, ["brew", "install", package], requires_sudo=False)

    def remove_plan(self, package: str) -> PackagePlan:
        return PackagePlan("remove", self.name, ["brew", "uninstall", package], requires_sudo=False)

    def update_plan(self) -> PackagePlan:
        return PackagePlan("update", self.name, ["brew", "update"], requires_sudo=False)

    def upgrade_plan(self) -> PackagePlan:
        return PackagePlan("upgrade", self.name, ["brew", "upgrade"], requires_sudo=False)

    def search_plan(self, query: str) -> PackagePlan:
        return PackagePlan("search", self.name, ["brew", "search", query], requires_sudo=False)

    def is_installed(self, package: str) -> bool:
        result = utils.run(["brew", "list", "--versions", package], timeout=10)
        return result.ok and bool(result.stdout)


# ---------------------------------------------------------------------------
# Windows backends
# ---------------------------------------------------------------------------


class WingetManager(PackageManagerBackend):
    name = "winget"
    binary = "winget"

    def install_plan(self, package: str) -> PackagePlan:
        return PackagePlan(
            "install", self.name,
            ["winget", "install", "--id", package, "-e", "--accept-source-agreements", "--accept-package-agreements"],
            requires_sudo=False,
        )

    def remove_plan(self, package: str) -> PackagePlan:
        return PackagePlan("remove", self.name, ["winget", "uninstall", "--id", package, "-e"], requires_sudo=False)

    def update_plan(self) -> PackagePlan:
        return PackagePlan("update", self.name, ["winget", "source", "update"], requires_sudo=False)

    def upgrade_plan(self) -> PackagePlan:
        return PackagePlan(
            "upgrade", self.name,
            ["winget", "upgrade", "--all", "--accept-source-agreements", "--accept-package-agreements"],
            requires_sudo=False,
        )

    def search_plan(self, query: str) -> PackagePlan:
        return PackagePlan("search", self.name, ["winget", "search", query], requires_sudo=False)

    def is_installed(self, package: str) -> bool:
        result = utils.run(["winget", "list", "--id", package, "-e"], timeout=15)
        return result.ok and package.lower() in (result.stdout or "").lower()


class ChocoManager(PackageManagerBackend):
    name = "choco"
    binary = "choco"

    def install_plan(self, package: str) -> PackagePlan:
        return PackagePlan("install", self.name, ["choco", "install", package, "-y"])

    def remove_plan(self, package: str) -> PackagePlan:
        return PackagePlan("remove", self.name, ["choco", "uninstall", package, "-y"])

    def update_plan(self) -> PackagePlan:
        return PackagePlan("update", self.name, ["choco", "outdated"])

    def upgrade_plan(self) -> PackagePlan:
        return PackagePlan("upgrade", self.name, ["choco", "upgrade", "all", "-y"])

    def search_plan(self, query: str) -> PackagePlan:
        return PackagePlan("search", self.name, ["choco", "search", query], requires_sudo=False)

    def is_installed(self, package: str) -> bool:
        result = utils.run(["choco", "list", "--local-only", package], timeout=15)
        return result.ok and package.lower() in (result.stdout or "").lower()


# Order matters: check the most likely-native manager first, but
# functionally the first available binary for the current OS wins.
_LINUX_BACKENDS = [AptManager, PacmanManager, DnfManager, YumManager, ZypperManager, ApkManager]
_MACOS_BACKENDS = [BrewManager]
_WINDOWS_BACKENDS = [WingetManager, ChocoManager]


def _candidate_backends():
    if utils.is_windows():
        return _WINDOWS_BACKENDS
    if utils.is_macos():
        return _MACOS_BACKENDS
    return _LINUX_BACKENDS


def get_backend() -> Optional[PackageManagerBackend]:
    """Return the first available package manager backend for this OS, or None."""
    for backend_cls in _candidate_backends():
        backend = backend_cls()
        if backend.is_available():
            return backend
    return None


def list_available_backends() -> List[str]:
    return [b().name for b in _candidate_backends() if b().is_available()]
