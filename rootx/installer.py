"""
rootx.installer
===============
App Installer: a curated catalogue of common applications/tools plus a
"Custom Package" flow. Everything goes through the Universal Package
Engine (rootx.packages) and every install is: detect -> show command ->
confirm -> execute -> verify. Nothing is ever piped from curl into a shell
without the user explicitly seeing the source and confirming first.

Package names are keyed per-backend so the same catalogue entry resolves
correctly on apt/pacman/dnf/yum/zypper/apk (Linux), brew (macOS) and
winget/choco (Windows).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from . import packages, security, utils

# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------


@dataclass
class CatalogEntry:
    key: str
    label: str
    package_names: dict          # package manager name -> package name
    verify_cmd: List[str]        # command run to verify installation, e.g. ["git", "--version"]
    description: str = ""
    security_tool: bool = False


CATALOG: List[CatalogEntry] = [
    CatalogEntry("1", "Git", {"*": "git", "winget": "Git.Git", "choco": "git"}, ["git", "--version"], "Distributed version control system."),
    CatalogEntry("2", "Python", {"*": "python3", "brew": "python", "winget": "Python.Python.3", "choco": "python"}, ["python3", "--version"], "Python 3 interpreter."),
    CatalogEntry("3", "Node.js", {"*": "nodejs", "apt": "nodejs", "brew": "node", "winget": "OpenJS.NodeJS", "choco": "nodejs"}, ["node", "--version"], "JavaScript runtime."),
    CatalogEntry("4", "Docker", {"*": "docker", "apt": "docker.io", "brew": "docker", "winget": "Docker.DockerDesktop", "choco": "docker-desktop"}, ["docker", "--version"], "Container platform."),
    CatalogEntry("5", "VS Code", {"*": "code", "brew": "visual-studio-code", "winget": "Microsoft.VisualStudioCode", "choco": "vscode"}, ["code", "--version"], "Source code editor."),
    CatalogEntry("6", "Firefox", {"*": "firefox", "brew": "firefox", "winget": "Mozilla.Firefox", "choco": "firefox"}, ["firefox", "--version"], "Web browser."),
    CatalogEntry("7", "Chromium", {"*": "chromium", "apt": "chromium-browser", "brew": "chromium", "winget": "eloston.ungoogled-chromium", "choco": "chromium"}, ["chromium", "--version"], "Open-source browser."),
    CatalogEntry("8", "Discord", {"*": "discord", "brew": "discord", "winget": "Discord.Discord", "choco": "discord"}, ["discord", "--version"], "Voice/text chat client (special handling)."),
    CatalogEntry("9", "Steam", {"*": "steam", "brew": "steam", "winget": "Valve.Steam", "choco": "steam"}, ["steam", "--version"], "Gaming platform."),
    CatalogEntry("10", "Neovim", {"*": "neovim", "apt": "neovim", "brew": "neovim", "winget": "Neovim.Neovim", "choco": "neovim"}, ["nvim", "--version"], "Modern Vim-based text editor."),
    CatalogEntry("11", "htop", {"*": "htop", "winget": "", "choco": ""}, ["htop", "--version"], "Interactive process viewer (Linux/macOS only)."),
    CatalogEntry("12", "curl", {"*": "curl", "winget": "cURL.cURL", "choco": "curl"}, ["curl", "--version"], "Command line data transfer tool."),
    CatalogEntry("13", "wget", {"*": "wget", "brew": "wget", "winget": "GnuWin32.Wget", "choco": "wget"}, ["wget", "--version"], "Command line file downloader."),
    CatalogEntry("14", "Nmap", {"*": "nmap", "winget": "Insecure.Nmap", "choco": "nmap"}, ["nmap", "--version"], "Network reconnaissance / port scanning.", security_tool=True),
    CatalogEntry("15", "Sherlock", {"*": "sherlock"}, ["sherlock", "--help"], "Username OSINT (installed via pipx).", security_tool=True),
    CatalogEntry("16", "Hydra", {"*": "hydra", "apt": "hydra", "pacman": "hydra", "dnf": "hydra", "brew": "hydra"}, ["hydra", "-h"], "Authentication auditing tool (Linux/macOS only).", security_tool=True),
]

SECURITY_TOOL_KEYS = {"14", "15", "16"}

# Entries with no usable package on the current OS resolve to "" and should
# be reported as unavailable instead of attempting a bogus install.
_WINDOWS_UNAVAILABLE = {"11", "16"}  # htop, hydra: no first-class Windows package


def get_entry(key: str) -> Optional[CatalogEntry]:
    for entry in CATALOG:
        if entry.key == key:
            return entry
    return None


def resolve_package_name(entry: CatalogEntry, backend_name: str) -> str:
    return entry.package_names.get(backend_name, entry.package_names.get("*", entry.label.lower()))


def is_available_on_current_os(entry: CatalogEntry) -> bool:
    if utils.is_windows() and entry.key in _WINDOWS_UNAVAILABLE:
        return False
    return True


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify_installed(verify_cmd: List[str]) -> utils.CommandResult:
    """Run only a safe --version/--help style check, never real functionality."""
    binary = verify_cmd[0]
    if not utils.command_exists(binary):
        return utils.CommandResult(
            ok=False,
            error="Installation appears successful, but executable was not found in PATH.",
        )
    return utils.run(verify_cmd, timeout=10)


# ---------------------------------------------------------------------------
# Standard catalogue install
# ---------------------------------------------------------------------------


def build_standard_plan(entry: CatalogEntry) -> Optional[packages.PackagePlan]:
    backend = packages.get_backend()
    if backend is None:
        return None
    if not is_available_on_current_os(entry):
        return None
    package_name = resolve_package_name(entry, backend.name)
    if not package_name or not utils.is_valid_package_name(package_name):
        return None
    return backend.install_plan(package_name)


# ---------------------------------------------------------------------------
# Sherlock: prefers pipx isolated install (cross-platform)
# ---------------------------------------------------------------------------


def build_sherlock_plan() -> dict:
    """
    Returns a dict describing the recommended install path for Sherlock.
    Preference order: pipx install sherlock-project > pip --user > unavailable.
    Never installs unnecessary system dependencies.
    """
    if utils.command_exists("pipx"):
        return {
            "method": "pipx",
            "command": ["pipx", "install", "sherlock-project"],
            "requires_sudo": False,
            "description": "Installs Sherlock in an isolated environment via pipx (recommended).",
        }
    pip_bin = None
    for candidate in ("pip3", "pip"):
        if utils.command_exists(candidate):
            pip_bin = candidate
            break
    if pip_bin:
        return {
            "method": "pip",
            "command": [pip_bin, "install", "--user", "sherlock-project"],
            "requires_sudo": False,
            "description": "pipx not found; falling back to 'pip install --user'.",
        }
    return {
        "method": "unavailable",
        "command": [],
        "requires_sudo": False,
        "description": "Neither pipx nor pip is available. Install Python's pip first.",
    }


# ---------------------------------------------------------------------------
# Discord: OS/distro/arch aware, no blind curl|bash
# ---------------------------------------------------------------------------


def build_discord_plan(distro_id: str, arch: str) -> dict:
    """
    Discord does not ship one universal package across every OS/distro. We
    only ever propose an OFFICIAL, verifiable method and show the source to
    the user; we never execute 'curl | bash' or unsigned installer downloads.
    """
    if utils.is_windows():
        if utils.command_exists("winget"):
            return {
                "method": "winget",
                "command": ["winget", "install", "--id", "Discord.Discord", "-e",
                            "--accept-source-agreements", "--accept-package-agreements"],
                "source": "winget (Microsoft's official package manager) - Discord.Discord",
                "description": "Installs Discord via winget from its official package manifest.",
            }
        return {
            "method": "manual_official",
            "command": [],
            "source": "https://discord.com/download (official Discord downloads page)",
            "description": "winget was not found. Please download the official installer manually.",
        }

    if utils.is_macos():
        if utils.command_exists("brew"):
            return {
                "method": "brew_cask",
                "command": ["brew", "install", "--cask", "discord"],
                "source": "Homebrew Cask (community-maintained, tracks official releases)",
                "description": "Installs Discord via Homebrew Cask.",
            }
        return {
            "method": "manual_official",
            "command": [],
            "source": "https://discord.com/download (official Discord downloads page)",
            "description": "Homebrew was not found. Please download the official installer manually.",
        }

    # Linux
    if arch not in ("x86_64",):
        return {
            "method": "unsupported_arch",
            "command": [],
            "source": None,
            "description": (
                f"No compatible official Discord package found for architecture '{arch}'. "
                "The application cannot safely install this package automatically."
            ),
        }

    if distro_id in ("arch", "manjaro", "endeavouros"):
        return {
            "method": "pacman_aur_note",
            "command": ["pacman", "-S", "discord"],
            "source": "Arch 'extra' or AUR (community-maintained) repository",
            "description": (
                "On Arch-based systems Discord may be available directly via pacman, "
                "or through the AUR using an AUR helper if not present in official repos."
            ),
        }

    if distro_id in ("fedora", "rhel", "rocky", "almalinux"):
        return {
            "method": "flatpak_recommended",
            "command": ["flatpak", "install", "-y", "flathub", "com.discordapp.Discord"],
            "source": "Flathub (official Flatpak remote) - com.discordapp.Discord",
            "description": (
                "No native RPM in default Fedora/RHEL-family repos. "
                "Recommended official alternative: Flatpak via Flathub."
            ),
        }

    return {
        "method": "manual_official",
        "command": [],
        "source": "https://discord.com/download (official Discord downloads page)",
        "description": (
            "Discord provides an official .deb package for Debian/Ubuntu-based systems. "
            "ROOT//X does not auto-download third-party installers; please download it "
            "manually from the official page, or install via Flatpak/Snap if preferred."
        ),
    }
