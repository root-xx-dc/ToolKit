"""
ROOT//X TOOLKIT — CLI interface v2.0.0

Integrates:
- Language selector at startup (EN / PL)
- Hardened license system with tier awareness (Bronze / Silver / Gold)
- All 11 new modules (Firewall, Logs, Scheduler, Users, Docker, Env, Backup, Ports, Git, Update, Benchmark)
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Tuple

from rootx import (
    autostart,
    backup,
    benchmark,
    debloater,
    docker_center,
    doctor as doctor_module,
    env_manager,
    fileshare,
    firewall,
    git_helper,
    hash_tool,
    installer,
    live_monitor,
    logs,
    network,
    packages,
    ports,
    processes,
    ram_cleaner,
    reports,
    scheduler,
    security,
    self_updater,
    services,
    smart_disk,
    ssl_inspector,
    storage,
    system,
    themes,
    tickets,
    update_center,
    users as users_module,
    utils,
    webpanel,
)
from rootx._config import ASCII_LOGO, AUTHOR, PRODUCT_NAME, VERSION
from rootx.lang import get_active_language, has_saved_language, load_language, save_language
from rootx.license import (
    LicenseResult,
    deactivate,
    get_saved_token,
    has_tier,
    is_activated,
    verify_token,
)

# Global active language strings dict
T: Dict[str, str] = load_language()


def _update_language(code: str) -> None:
    global T
    save_language(code)
    T = load_language(code)


# ─── ANSI colors ──────────────────────────────────────────────────────────

class ColorTheme:
    @property
    def RESET(self) -> str: return themes.get_active_theme().get("reset", "\033[0m")
    @property
    def BOLD(self) -> str: return themes.get_active_theme().get("bold", "\033[1m")
    @property
    def RED(self) -> str: return themes.get_active_theme().get("error", "\033[91m")
    @property
    def GREEN(self) -> str: return themes.get_active_theme().get("success", "\033[92m")
    @property
    def YELLOW(self) -> str: return themes.get_active_theme().get("warning", "\033[93m")
    @property
    def CYAN(self) -> str: return themes.get_active_theme().get("primary", "\033[96m")
    @property
    def WHITE(self) -> str: return themes.get_active_theme().get("white", "\033[97m")
    @property
    def DIM(self) -> str: return themes.get_active_theme().get("dim", "\033[2m")

C = ColorTheme()


def _enable_ansi_windows() -> None:
    """Enables ANSI colors in Windows CMD/PowerShell."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


def _clear() -> None:
    os.system("cls" if sys.platform == "win32" else "clear")


# ─── Banner ───────────────────────────────────────────────────────────────────

def _make_banner() -> str:
    lines = []
    lines.append("")
    for line in ASCII_LOGO.splitlines():
        if line.strip():
            lines.append(f"  {C.CYAN}{C.BOLD}{line}{C.RESET}")
    lines.append(f"  {C.YELLOW}{'─' * 50}{C.RESET}")
    lines.append(f"  {C.DIM}v{VERSION}  ·  by {AUTHOR}{C.RESET}")
    lines.append("")
    return "\n".join(lines)


BANNER = _make_banner()


# ─── Small presentation helpers ───────────────────────────────────────────

def _rule(char: str = "─", width: int = 54) -> str:
    return char * width


def _ask(prompt_text: str) -> str:
    try:
        return input(f"  {C.CYAN}{prompt_text} >{C.RESET} ").strip()
    except (KeyboardInterrupt, EOFError):
        raise


def _confirm(question: str, default: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        answer = input(f"  {C.YELLOW}{question} {suffix}:{C.RESET} ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        raise
    if not answer:
        return default
    return answer in ("y", "yes")


def _pause() -> None:
    try:
        input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")
    except (KeyboardInterrupt, EOFError):
        raise


def _info(message: str, title: str = "INFO") -> None:
    print(f"\n  {C.CYAN}[{title}]{C.RESET} {message}")


def _success(message: str) -> None:
    print(f"\n  {C.GREEN}✓ {message}{C.RESET}")


def _warning(message: str) -> None:
    print(f"\n  {C.YELLOW}⚠ {message}{C.RESET}")


def _error(message: str, exit_code: int | None = None) -> None:
    suffix = f" (exit code: {exit_code})" if exit_code is not None else ""
    print(f"\n  {C.RED}✗ {message}{suffix}{C.RESET}")


def _status_line(label: str, ok: bool | None, detail: str = "") -> None:
    if ok is True:
        marker, color = "[✓]", C.GREEN
    elif ok is False:
        marker, color = "[✗]", C.RED
    else:
        marker, color = "[!]", C.YELLOW
    tail = f"  {C.DIM}{detail}{C.RESET}" if detail else ""
    print(f"  {color}{marker} {label}{C.RESET}{tail}")


def _render_menu(title: str, options: List[Tuple[str, str]]) -> None:
    print(f"\n  {C.YELLOW}{_rule()}{C.RESET}")
    if title:
        print(f"  {C.BOLD}{title}{C.RESET}")
        print(f"  {C.YELLOW}{_rule()}{C.RESET}")
    for key, label in options:
        print(f"  {C.CYAN}[{key}]{C.RESET} {label}")
    print(f"  {C.YELLOW}{_rule()}{C.RESET}")


def _print_table(title: str, columns: List[str], rows: List[List[Any]]) -> None:
    print(f"\n  {C.BOLD}{title}{C.RESET}")
    widths = [len(c) for c in columns]
    str_rows = [[str(cell) for cell in row] for row in rows]
    for row in str_rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))
    header = "  " + "  ".join(c.ljust(widths[i]) for i, c in enumerate(columns))
    print(f"  {C.CYAN}{header}{C.RESET}")
    print(f"  {C.DIM}{_rule('-', len(header))}{C.RESET}")
    if not str_rows:
        print(f"  {C.DIM}(no data){C.RESET}")
    for row in str_rows:
        line = "  " + "  ".join(cell.ljust(widths[i]) if i < len(widths) else cell for i, cell in enumerate(row))
        print(f"  {line}")


def _print_command_box(title: str, fields: Dict[str, Any]) -> None:
    print(f"\n  {C.BOLD}{title}{C.RESET}")
    for key, value in fields.items():
        print(f"    {C.BOLD}{key}:{C.RESET} {value}")


# ─── Language picker screen ───────────────────────────────────────────────

def _language_picker_screen() -> None:
    """Select language on first launch."""
    _clear()
    print(BANNER)
    print(f"  {C.YELLOW}{'━' * 50}{C.RESET}")
    print(f"  {C.BOLD}{C.WHITE}  SELECT LANGUAGE / WYBIERZ JĘZYK{C.RESET}")
    print(f"  {C.YELLOW}{'━' * 50}{C.RESET}\n")
    print("  \033[96m[1]\033[0m  English")
    print("  \033[96m[2]\033[0m  Polski\n")

    while True:
        try:
            choice = input("  \033[96mChoice / Wybór >\033[0m ").strip()
        except (KeyboardInterrupt, EOFError):
            sys.exit(0)
        if choice == "1":
            _update_language("en")
            break
        elif choice == "2":
            _update_language("pl")
            break
        else:
            print("  \033[91m✗ Invalid choice / Nieprawidłowy wybór.\033[0m")


# ─── Activation screen ────────────────────────────────────────────────────

def _activation_screen() -> bool:
    _clear()
    print(BANNER)
    print(f"  {C.YELLOW}{'━' * 50}{C.RESET}")
    print(f"  {C.BOLD}{C.WHITE}  {T.get('activate_title', 'LICENSE ACTIVATION')}{C.RESET}")
    print(f"  {C.YELLOW}{'━' * 50}{C.RESET}")
    print(f"  {C.DIM}  {T.get('activate_hint', 'Paste the key you received via Discord DM.')}{C.RESET}")
    print(f"  {C.YELLOW}{'━' * 50}{C.RESET}\n")

    while True:
        try:
            token = input(f"  {C.CYAN}{T.get('activate_prompt', 'License key')}:{C.RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n  {C.DIM}{T.get('cancelled', 'Cancelled.')}{C.RESET}")
            return False

        if not token:
            print(f"  {C.RED}✗ {T.get('activate_empty', 'Key cannot be empty.')}{C.RESET}\n")
            continue

        print(f"\n  {C.DIM}{T.get('activate_verifying', 'Verifying...')}{C.RESET}", end="", flush=True)
        result: LicenseResult = verify_token(token)

        if result.valid:
            print(f"\r  {C.GREEN}✓ {T.get('activate_success', 'Key accepted! Welcome to ROOT//X TOOLKIT.')}{C.RESET}\n")
            return True
        else:
            print(f"\r  {C.RED}✗ {result.reason}{C.RESET}\n")
            print(f"  {C.DIM}{T.get('activate_retry', 'Try again or contact the administrator.')}{C.RESET}\n")


# ─── ROOT//X DOCTOR ─────────────────────────────────────────────────────────

def _doctor_summary(report: Any) -> None:
    print()
    print(f"  {C.BOLD}{C.CYAN}ROOT//X DOCTOR{C.RESET}")
    print(f"  {C.DIM}{_rule()}{C.RESET}")
    _status_line("System", True)
    _status_line(
        "Storage",
        len(report.storage_result["criticals"]) == 0 and len(report.storage_result["warnings"]) == 0,
    )
    _status_line("Network", report.network_result.internet_ok)
    _status_line("Package Manager", report.package_manager is not None)
    _status_line(
        "Services",
        len(report.failed_services) == 0,
        "" if not report.failed_services else f"{len(report.failed_services)} failed",
    )
    print(f"\n  {C.BOLD}Problems detected:{C.RESET} {report.problem_count}")
    for finding in report.warnings:
        _warning(finding.message)
    for finding in report.criticals:
        _error(finding.message)


def doctor_screen() -> None:
    print(f"\n  {C.DIM}Running ROOT//X DOCTOR diagnostics...{C.RESET}")
    report = doctor_module.run_diagnostics()
    _doctor_summary(report)

    while True:
        _render_menu("", [
            ("1", "Fix automatically"),
            ("2", "Show details"),
            ("3", "Export report"),
            ("4", T.get("doctor_ticket_opt", "Submit ticket to Support Staff [Gold Tier]")),
            ("0", "Back"),
        ])
        choice = _ask("doctor")
        if choice == "0":
            return
        elif choice == "1":
            _doctor_fix_screen(report)
        elif choice == "2":
            _doctor_details_screen(report)
        elif choice == "3":
            _doctor_export_screen(report)
        elif choice == "4":
            _doctor_submit_ticket_flow(report)


def _doctor_submit_ticket_flow(report: Any) -> None:
    saved_token = get_saved_token()
    res_lic = verify_token(saved_token) if saved_token else LicenseResult(False)

    if not has_tier(res_lic, "gold"):
        _warning(T.get("doctor_ticket_gold_req", "Submitting support tickets to Discord staff is a Gold Tier feature."))
        _pause()
        return

    if not _confirm(T.get("doctor_ticket_confirm", "Do you want to send this report and open a support ticket on Discord?"), default=False):
        return

    desc = _ask(T.get("doctor_ticket_prompt", "Briefly describe the issue you are experiencing"))
    if not desc:
        _error("Problem description cannot be empty.")
        _pause()
        return

    from rootx.license import _hash_token
    token_hash = _hash_token(saved_token) if saved_token else "unknown"

    print(f"  {C.DIM}Submitting ticket...{C.RESET}")
    ok, msg = tickets.submit_doctor_ticket(desc, report, token_hash)
    if ok:
        _success(T.get("doctor_ticket_success", "Ticket submitted successfully! Discord bot will open a support ticket on the server for you."))
    else:
        _error(msg)
    _pause()


def _doctor_details_screen(report: Any) -> None:
    s = report.system_info
    _print_table("System", ["Field", "Value"], [
        ["OS / Distro", f"{s.distro_name} {s.distro_version}"],
        ["Kernel", s.kernel],
        ["Architecture", s.architecture],
        ["Hostname", s.hostname],
        ["Uptime", s.uptime],
    ])
    _print_table("Storage", ["Mount", "Used/Size", "Percent", "Level"],
                 [[m.mount_point, f"{m.used}/{m.size}", f"{m.percent}%", m.level] for m in report.storage_result["mounts"]])
    net = report.network_result
    _print_table("Network", ["Field", "Value"], [
        ["Interface", net.interface_name],
        ["Local IP", net.local_ip],
        ["Gateway", net.gateway_ip],
        ["Gateway reachable", str(net.gateway_ok)],
        ["DNS OK", str(net.dns_ok)],
        ["Internet OK", str(net.internet_ok)],
    ])
    if report.failed_services:
        _print_table("Failed/Stopped Services", ["Name", "Active", "Sub"],
                     [[svc.name, svc.active, svc.sub] for svc in report.failed_services])
    _pause()


def _doctor_fix_screen(report: Any) -> None:
    fixes = doctor_module.get_safe_fixes(report)
    if not fixes:
        _info("No automatic safe fixes are applicable right now.")
        _pause()
        return

    for fix in fixes:
        _print_command_box("PROPOSED FIX", {
            "Problem": fix.problem,
            "Command": fix.build_display_command(),
            "Description": fix.description,
        })
        if security.is_dangerous(fix.command):
            _error("This fix was blocked by the internal safety denylist.")
            continue
        notice = utils.needs_admin_notice()
        if notice and fix.requires_sudo:
            _warning(notice)
        if _confirm("Continue?", default=False):
            result = fix.execute()
            if result.ok:
                _success(f"Fix applied: {fix.problem}")
            else:
                _error(result.error or result.stderr or "Fix failed.", result.returncode)
        else:
            _info("Skipped.")
    _pause()


def _doctor_export_screen(report: Any) -> None:
    _warning(
        "The report may contain system information such as hostname, local IP, "
        "installed services, and disk usage. No passwords, tokens or secrets are ever included."
    )
    if not _confirm("Generate rootx-report.txt in the current directory?", default=True):
        return
    try:
        path = reports.write_report(report)
        _success(f"Report written to:\n  {path}")
    except Exception as exc:
        _error(f"Failed to write report: {exc}")
    _pause()


# ─── APP INSTALLER ─────────────────────────────────────────────────────────

INSTALLER_MENU_OPTIONS = [
    ("1", "Git"), ("2", "Python"), ("3", "Node.js"), ("4", "Docker"),
    ("5", "VS Code"), ("6", "Firefox"), ("7", "Chromium"), ("8", "Discord"),
    ("9", "Steam"), ("10", "Neovim"), ("11", "htop"), ("12", "curl"), ("13", "wget"),
    ("14", "Nmap  [security]"), ("15", "Sherlock  [security]"), ("16", "Hydra  [security]"),
    ("17", "Custom Package"), ("0", "Back"),
]


def installer_screen() -> None:
    while True:
        _render_menu("APP INSTALLER", INSTALLER_MENU_OPTIONS)
        choice = _ask("installer")
        if choice == "0":
            return
        elif choice == "17":
            _custom_package_flow()
        elif choice == "8":
            _discord_install_flow()
        elif choice == "15":
            _sherlock_install_flow()
        else:
            entry = installer.get_entry(choice)
            if entry:
                _standard_install_flow(entry)


def _standard_install_flow(entry: Any) -> None:
    if not installer.is_available_on_current_os(entry):
        _warning(f"{entry.label} has no first-class package on {utils.os_name()}.")
        _pause()
        return

    backend = packages.get_backend()
    if backend is None:
        _error("No supported package manager was detected on this system.")
        _pause()
        return

    distro = utils.detect_distro()
    arch = utils.detect_architecture()

    if entry.security_tool:
        _info(entry.description, title=f"SECURITY TOOL: {entry.label}")

    package_name = installer.resolve_package_name(entry, backend.name)
    if not package_name:
        _warning(f"{entry.label} has no package mapping for {backend.name}.")
        _pause()
        return

    if backend.is_installed(package_name):
        _info(f"{entry.label} appears to already be installed.")
        _pause()
        return

    plan = backend.install_plan(package_name)
    _print_command_box("INSTALLATION", {
        "Package": package_name,
        "OS": f"{distro['name']} ({utils.os_name()})",
        "Architecture": arch,
        "Package manager": backend.name,
        "Command": plan.display_command,
    })

    if security.is_dangerous(plan.command):
        _error("Blocked by internal safety policy.")
        return

    notice = utils.needs_admin_notice()
    if notice and plan.requires_sudo:
        _warning(notice)

    if not _confirm("Continue?", default=False):
        _info("Installation cancelled.")
        return

    print(f"  {C.DIM}Installing {entry.label}...{C.RESET}")
    result = backend.execute(plan)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"  {C.DIM}{result.stderr}{C.RESET}")

    if result.ok:
        _success("Installation completed.")
        verify = installer.verify_installed(entry.verify_cmd)
        if verify.ok:
            _info(verify.stdout or "Verified.", title="Version")
        else:
            _warning(verify.error or "Could not verify installation.")
    else:
        _error(result.error or result.stderr or "Installation failed.", result.returncode)

    _pause()


def _discord_install_flow() -> None:
    distro = utils.detect_distro()
    arch = utils.detect_architecture()

    if utils.command_exists("discord"):
        _info("Discord appears to already be installed.")
        _pause()
        return

    plan = installer.build_discord_plan(distro["id"], arch)
    _print_command_box("DISCORD INSTALLATION", {
        "OS": f"{distro['name']} ({utils.os_name()})",
        "Architecture": arch,
        "Method": plan["method"],
        "Source": plan["source"] or "N/A",
    })
    _info(plan["description"], title="Discord")

    if not plan["command"]:
        _pause()
        return

    prefix = utils.sudo_prefix()
    display_cmd = " ".join(prefix + plan["command"])
    print(f"\n  {C.BOLD}Proposed command:{C.RESET}\n  {display_cmd}\n")

    if security.is_dangerous(plan["command"]):
        _error("Blocked by internal safety policy.")
        return

    if not _confirm("Continue?", default=False):
        _info("Installation cancelled.")
        return

    print(f"  {C.DIM}Installing Discord...{C.RESET}")
    result = utils.run(prefix + plan["command"], timeout=300)

    if result.ok:
        _success("Installation completed.")
    else:
        _error(result.error or result.stderr or "Installation failed.", result.returncode)
    _pause()


def _sherlock_install_flow() -> None:
    _info(
        "Sherlock is an OSINT tool used to search for usernames across public sites. "
        "ROOT//X will not run any username search during installation.",
        title="SECURITY TOOL: Sherlock",
    )

    if utils.command_exists("sherlock"):
        _info("Sherlock appears to already be installed.")
        _pause()
        return

    plan = installer.build_sherlock_plan()
    if plan["method"] == "unavailable":
        _error(plan["description"])
        _pause()
        return

    _print_command_box("SHERLOCK INSTALLATION", {
        "Method": plan["method"], "Command": " ".join(plan["command"]), "Notes": plan["description"],
    })

    if not _confirm("Continue?", default=False):
        _info("Installation cancelled.")
        return

    print(f"  {C.DIM}Installing Sherlock...{C.RESET}")
    result = utils.run(plan["command"], timeout=180)

    if result.ok:
        _success("Installation completed.")
        verify = installer.verify_installed(["sherlock", "--help"])
        if verify.ok:
            _info("sherlock --help executed successfully.", title="Verification")
        else:
            _warning(verify.error or "Could not verify installation.")
    else:
        _error(result.error or result.stderr or "Installation failed.", result.returncode)
    _pause()


def _custom_package_flow() -> None:
    backend = packages.get_backend()
    if backend is None:
        _error("No supported package manager was detected on this system.")
        _pause()
        return

    query = _ask("package name")
    if not utils.is_valid_package_name(query):
        _error("Invalid package name. Only letters, digits, '.', '_', '+' and '-' are allowed.")
        _pause()
        return

    print(f"  {C.DIM}Searching for '{query}'...{C.RESET}")
    result = backend.search(query)

    if not result.ok or not result.stdout:
        _warning(f"No results found for '{query}'.")
        _pause()
        return

    print(result.stdout[:3000])

    if not _confirm(f"Install package '{query}' using {backend.name}?", default=False):
        return

    plan = backend.install_plan(query)
    _print_command_box("INSTALLATION", {"Package": query, "Package manager": backend.name, "Command": plan.display_command})

    if security.is_dangerous(plan.command):
        _error("Blocked by internal safety policy.")
        return

    if not _confirm("Continue?", default=False):
        _info("Installation cancelled.")
        return

    print(f"  {C.DIM}Installing {query}...{C.RESET}")
    exec_result = backend.execute(plan)

    if exec_result.ok:
        _success("Installation completed.")
    else:
        _error(exec_result.error or exec_result.stderr or "Installation failed.", exec_result.returncode)
    _pause()


# ─── NETWORK CENTER ─────────────────────────────────────────────────────────

def network_screen() -> None:
    while True:
        _render_menu("NETWORK CENTER", [
            ("1", "Overview"), ("2", "Network Doctor"), ("3", "Ping a host"),
            ("4", "DNS lookup"), ("5", "Traceroute"), ("6", "Public IP (opt-in)"),
            ("7", "Active connections"), ("0", "Back"),
        ])
        choice = _ask("network")
        if choice == "0":
            return
        if choice == "1":
            _network_overview()
        elif choice == "2":
            _network_doctor()
        elif choice == "3":
            host = _ask("host to ping")
            ok = network.ping_host(host)
            (_success if ok else _error)(f"Ping to {host}: {'reachable' if ok else 'unreachable'}")
        elif choice == "4":
            host = _ask("hostname to resolve")
            ip = network.dns_lookup(host)
            (_success if ip else _error)(f"{host} -> {ip or 'resolution failed'}")
        elif choice == "5":
            host = _ask("host to traceroute")
            output = network.traceroute(host)
            print(output if output else f"  {C.DIM}traceroute/tracert is not available on this system.{C.RESET}")
        elif choice == "6":
            if _confirm("This will make an outbound request to detect your public IP. Continue?", default=False):
                ip = network.get_public_ip()
                (_success if ip else _error)(f"Public IP: {ip or 'could not be determined'}")
        elif choice == "7":
            conns = network.get_active_connections()
            print("\n".join(conns) if conns else f"  {C.DIM}No data available.{C.RESET}")
        _pause()


def _network_overview() -> None:
    interfaces = network.get_interfaces()
    _print_table("Network Overview", ["Field", "Value"], [
        ["Interfaces", ", ".join(interfaces) or "N/A"],
        ["Local IP", network.get_local_ip()],
        ["Gateway", network.get_gateway()],
        ["DNS servers", ", ".join(network.get_dns_servers()) or "N/A"],
    ])


def _network_doctor() -> None:
    print(f"  {C.DIM}Running Network Doctor...{C.RESET}")
    result = network.network_doctor()
    _status_line("Interface detected", result.interface_ok, result.interface_name)
    _status_line("IP address", result.ip_ok, result.local_ip)
    _status_line("Gateway reachable", result.gateway_ok, result.gateway_ip)
    _status_line("DNS", result.dns_ok)
    _status_line("Internet", result.internet_ok)
    if result.suggestion:
        _warning(result.suggestion)


# ─── DISK CENTER ────────────────────────────────────────────────────────────

def disk_screen() -> None:
    while True:
        _render_menu("DISK CENTER", [
            ("1", "Usage overview"), ("2", "Block devices / volumes"),
            ("3", "Find large files"), ("0", "Back"),
        ])
        choice = _ask("disk")
        if choice == "0":
            return
        if choice == "1":
            mounts = storage.get_df()
            _print_table("Disk Usage", ["Mount", "FS", "Size", "Used", "Available", "Use%", "Level"],
                         [[m.mount_point, m.filesystem, m.size, m.used, m.available, f"{m.percent}%", m.level] for m in mounts])
        elif choice == "2":
            output = storage.get_lsblk()
            print(output if output else f"  {C.DIM}Block device listing unavailable on this system.{C.RESET}")
        elif choice == "3":
            _find_large_files_flow()
        _pause()


def _find_large_files_flow() -> None:
    _render_menu("Find Large Files", [("1", ">100 MB"), ("2", ">500 MB"), ("3", ">1 GB"), ("0", "Back")])
    choice = _ask("size")
    if choice == "0":
        return
    min_mb = {"1": 100, "2": 500, "3": 1024}.get(choice)
    if min_mb is None:
        return
    default_path = os.path.expanduser("~")
    path = _ask(f"search path (default: {default_path})") or default_path
    print(f"  {C.DIM}Searching {path} for files > {min_mb}MB...{C.RESET}")
    results = storage.find_large_files(path=path, min_mb=min_mb)
    if results:
        for line in results:
            print(f"  {line}")
    else:
        _info("No matching files found (or path inaccessible).")


# ─── PROCESS CENTER ─────────────────────────────────────────────────────────

def process_screen() -> None:
    procs = processes.list_processes()
    while True:
        _print_table("Process Center (top 20 by CPU)", ["PID", "USER", "CPU%", "MEM%", "COMMAND"],
                     [[p.pid, p.user, p.cpu, p.mem, p.command] for p in procs[:20]])
        _render_menu("", [
            ("1", "Sort by CPU"), ("2", "Sort by RAM"), ("3", "Search"),
            ("4", "Refresh"), ("5", "Kill process"), ("0", "Back"),
        ])
        choice = _ask("process")
        if choice == "0":
            return
        elif choice == "1":
            procs = processes.sort_by_cpu(procs)
        elif choice == "2":
            procs = processes.sort_by_mem(procs)
        elif choice == "3":
            query = _ask("search term")
            procs = processes.search_processes(processes.list_processes(), query)
        elif choice == "4":
            procs = processes.list_processes()
        elif choice == "5":
            _kill_process_flow()
            procs = processes.list_processes()


def _kill_process_flow() -> None:
    pid = _ask("PID to kill")
    procs = processes.list_processes()
    target = next((p for p in procs if p.pid == pid), None)
    if target is None:
        _error(f"No process found with PID {pid}.")
        return
    if processes.is_protected(target):
        _error(f"Refusing to kill protected/system process: {target.command}")
        return

    _print_command_box("KILL PROCESS", {"PID": target.pid, "Name": target.command, "User": target.user})
    if not _confirm("Are you sure?", default=False):
        return
    result = processes.kill_process(pid)
    (_success if result.ok else _error)(result.stdout or result.error or "Unknown result.")


# ─── SERVICE MANAGER ────────────────────────────────────────────────────────

def service_screen() -> None:
    if not services.service_manager_available():
        _warning("The service manager is not available on this system.")
        return

    while True:
        _render_menu("SERVICE MANAGER", [
            ("1", "Running services"), ("2", "Failed services"), ("3", "Stopped services"),
            ("4", "Control a service"), ("0", "Back"),
        ])
        choice = _ask("services")
        if choice == "0":
            return
        elif choice == "1":
            _list_services("running")
        elif choice == "2":
            _list_services("failed")
        elif choice == "3":
            _list_services("stopped")
        elif choice == "4":
            _control_service_flow()
        _pause()


def _list_services(state: str) -> None:
    svc_list = services.list_services(state)
    _print_table(f"Services ({state})", ["Name", "Load", "Active", "Sub"],
                 [[s.name, s.load, s.active, s.sub] for s in svc_list] or [["-", "-", "-", "-"]])


def _control_service_flow() -> None:
    hint = "e.g. sshd.service" if utils.is_linux() else ("e.g. Spooler" if utils.is_windows() else "e.g. com.example.agent")
    name = _ask(f"service name ({hint})")
    _render_menu("", [
        ("1", "status"), ("2", "start"), ("3", "stop"), ("4", "restart"),
        ("5", "enable"), ("6", "disable"), ("7", "logs"), ("0", "Back"),
    ])
    choice = _ask("action")
    if choice == "0":
        return

    if choice == "1":
        result = services.service_status(name)
        print(result.stdout or result.error or "No output.")
        return
    if choice == "7":
        result = services.service_logs(name)
        print(result.stdout or result.error or "No output.")
        return

    actions = {
        "2": ("start", services.start_service), "3": ("stop", services.stop_service),
        "4": ("restart", services.restart_service), "5": ("enable", services.enable_service),
        "6": ("disable", services.disable_service),
    }
    if choice not in actions:
        return
    label, func = actions[choice]

    _print_command_box("SERVICE ACTION", {"Service": name, "Action": label, "OS": utils.os_name()})
    notice = utils.needs_admin_notice()
    if notice:
        _warning(notice)
    if not _confirm("Continue?", default=False):
        return
    result = func(name)
    (_success if result.ok else _error)(result.stdout or result.error or result.stderr or "Done.")


# ─── PACKAGE MANAGER ─────────────────────────────────────────────────────────

def package_manager_screen() -> None:
    backend = packages.get_backend()
    if backend is None:
        _error("No supported package manager was detected on this system.")
        _pause()
        return

    while True:
        _render_menu(f"PACKAGE MANAGER ({backend.name})", [
            ("1", "Update"), ("2", "Upgrade"), ("3", "Search"),
            ("4", "Install"), ("5", "Remove"), ("0", "Back"),
        ])
        choice = _ask("packages")
        if choice == "0":
            return

        if choice == "3":
            query = _ask("search term")
            result = backend.search(query)
            print(result.stdout[:3000] if result.stdout else "No results.")
            _pause()
            continue

        plan_map = {
            "1": ("update", backend.update_plan()),
            "2": ("upgrade", backend.upgrade_plan()),
        }
        if choice in plan_map:
            label, plan = plan_map[choice]
            _execute_plan_with_confirmation(backend, plan, label)
            _pause()
            continue

        if choice in ("4", "5"):
            pkg = _ask("package name")
            if not utils.is_valid_package_name(pkg):
                _error("Invalid package name.")
                _pause()
                continue
            plan = backend.install_plan(pkg) if choice == "4" else backend.remove_plan(pkg)
            label = "install" if choice == "4" else "remove"
            _execute_plan_with_confirmation(backend, plan, label)
            _pause()


def _execute_plan_with_confirmation(backend: Any, plan: Any, label: str) -> None:
    _print_command_box("PACKAGE MANAGER", {"Action": label, "Backend": backend.name, "Command": plan.display_command})
    if security.is_dangerous(plan.command):
        _error("Blocked by internal safety policy.")
        return
    notice = utils.needs_admin_notice()
    if notice and plan.requires_sudo:
        _warning(notice)
    if not _confirm("Continue?", default=False):
        _info("Cancelled.")
        return
    print(f"  {C.DIM}Running {label}...{C.RESET}")
    result = backend.execute(plan)
    if result.stdout:
        print(result.stdout[:4000])
    if result.ok:
        _success(f"{label.capitalize()} completed.")
    else:
        _error(result.error or result.stderr or f"{label} failed.", result.returncode)


# ─── SYSTEM INFORMATION ─────────────────────────────────────────────────────

def system_info_screen() -> None:
    info = system.collect()
    _print_table("System Information", ["Field", "Value"], [
        ["OS / Distro", f"{info.distro_name} {info.distro_version}"],
        ["Kernel", info.kernel],
        ["Architecture", info.architecture],
        ["CPU", info.cpu_model],
        ["Cores", info.cpu_cores],
        ["RAM total", info.ram_total],
        ["RAM available", info.ram_available],
        ["Swap total", info.swap_total],
        ["Swap used", info.swap_used],
        ["GPU", info.gpu],
        ["Hostname", info.hostname],
        ["Uptime", info.uptime],
        ["Disk (root)", info.disk_summary],
        ["Shell", info.shell],
        ["Motherboard", info.motherboard],
        ["BIOS", info.bios],
        ["Temperature", info.temperature],
    ])
    _pause()


# ─── DIAGNOSTIC REPORT ──────────────────────────────────────────────────────

def report_screen() -> None:
    print(f"  {C.DIM}Collecting diagnostic data...{C.RESET}")
    report = doctor_module.run_diagnostics()
    _doctor_export_screen(report)


# ─── NEW MODULE SCREENS ─────────────────────────────────────────────────────

# 1. Firewall Center (Silver+)
def firewall_screen() -> None:
    if utils.is_macos():
        _warning(T.get("fw_not_available", "Firewall Center is not available on macOS."))
        _pause()
        return

    while True:
        status = firewall.get_status()
        status_str = "Enabled" if status.enabled else "Disabled"
        _render_menu(f"{T.get('fw_title', 'FIREWALL CENTER')} [{status.backend.upper()}: {status_str}]", [
            ("1", "Status & overview"),
            ("2", "List active rules"),
            ("3", "Add rule"),
            ("4", "Remove rule"),
            ("5", "Enable / Disable firewall"),
            ("0", "Back"),
        ])
        choice = _ask("firewall")
        if choice == "0":
            return
        elif choice == "1":
            _info(status.details or "No details available.", title="Firewall Overview")
        elif choice == "2":
            rules = firewall.list_rules()
            _print_table("Active Rules", ["ID", "Direction", "Action", "Port", "Protocol", "Source"],
                         [[r.rule_id, r.direction, r.action, r.port, r.protocol, r.source] for r in rules])
        elif choice == "3":
            port = _ask("port (e.g. 80)")
            proto = _ask("protocol (tcp/udp, default tcp)") or "tcp"
            action = _ask("action (allow/deny, default allow)") or "allow"
            direction = _ask("direction (in/out, default in)") or "in"
            res = firewall.add_rule(port, proto, action, direction)
            if "error" in res:
                _error(res["error"])
            else:
                _print_command_box("ADD FIREWALL RULE", {"Backend": res["backend"], "Command": res["display"]})
                if security.is_dangerous(res["command"]):
                    _error("Blocked by security policy.")
                elif _confirm("Execute command?", default=False):
                    cmd_res = utils.run(utils.sudo_prefix() + res["command"], timeout=30)
                    (_success if cmd_res.ok else _error)(cmd_res.stdout or cmd_res.error or "Failed.")
        elif choice == "4":
            rule_id = _ask("rule ID to remove")
            res = firewall.remove_rule(rule_id)
            if "error" in res:
                _error(res["error"])
            else:
                _print_command_box("REMOVE FIREWALL RULE", {"Backend": res["backend"], "Command": res["display"]})
                if _confirm("Execute command?", default=False):
                    cmd_res = utils.run(utils.sudo_prefix() + res["command"], timeout=30)
                    (_success if cmd_res.ok else _error)(cmd_res.stdout or cmd_res.error or "Failed.")
        elif choice == "5":
            target = not status.enabled
            res = firewall.set_enabled(target)
            if "error" in res:
                _error(res["error"])
            else:
                act = "Enable" if target else "Disable"
                _print_command_box(f"{act} FIREWALL", {"Backend": res["backend"], "Command": res["display"]})
                if _confirm(f"Are you sure you want to {act.lower()} the firewall?", default=False):
                    cmd_res = utils.run(utils.sudo_prefix() + res["command"], timeout=30)
                    (_success if cmd_res.ok else _error)(cmd_res.stdout or cmd_res.error or "Failed.")
        _pause()


# 2. Log Viewer (Silver+)
def logs_screen() -> None:
    while True:
        _render_menu(T.get("logs_title", "LOG VIEWER"), [
            ("1", "System log (last N lines)"),
            ("2", "Filter by level"),
            ("3", "Logs for a specific service"),
            ("4", "Browse /var/log/ files (Linux)"),
            ("0", "Back"),
        ])
        choice = _ask("logs")
        if choice == "0":
            return
        elif choice == "1":
            lines_str = _ask("number of lines (default 50)") or "50"
            lines_cnt = int(lines_str) if lines_str.isdigit() else 50
            if utils.is_windows():
                out = logs.read_windows_eventlog("System", "warning", lines_cnt)
            else:
                out = logs.read_journal("info", lines_cnt)
            print("\n" + out)
        elif choice == "2":
            lvl = _ask("level (critical/error/warning/info, default warning)") or "warning"
            lines_str = _ask("number of lines (default 50)") or "50"
            lines_cnt = int(lines_str) if lines_str.isdigit() else 50
            if utils.is_windows():
                out = logs.read_windows_eventlog("System", lvl, lines_cnt)
            else:
                out = logs.read_journal(lvl, lines_cnt)
            print("\n" + out)
        elif choice == "3":
            svc = _ask("service name")
            lines_str = _ask("number of lines (default 50)") or "50"
            lines_cnt = int(lines_str) if lines_str.isdigit() else 50
            out = logs.read_service_logs(svc, lines_cnt)
            print("\n" + out)
        elif choice == "4":
            if not utils.is_linux():
                _warning("File logging is only available on Linux.")
            else:
                var_files = logs.list_varlog_files()
                _print_table("Available /var/log Files", ["File"], [[f] for f in var_files])
                fname = _ask("filename to read (e.g. syslog)")
                if fname in var_files:
                    out = logs.read_file(f"/var/log/{fname}")
                    print("\n" + out[:4000])
                else:
                    _error("File not in list.")
        _pause()


# 3. Scheduler (Silver+)
def scheduler_screen() -> None:
    while True:
        _render_menu(T.get("sched_title", "TASK SCHEDULER"), [
            ("1", "List scheduled jobs"),
            ("2", "Add new cron job (Linux)"),
            ("3", "Remove cron job (Linux)"),
            ("0", "Back"),
        ])
        choice = _ask("scheduler")
        if choice == "0":
            return
        elif choice == "1":
            if utils.is_windows():
                out = scheduler.list_windows_tasks()
                print("\n" + out[:4000])
            else:
                jobs = scheduler.list_jobs()
                _print_table("Scheduled Cron Jobs", ["Index", "Schedule", "Command"],
                             [[j.index, j.schedule, j.command] for j in jobs])
        elif choice == "2":
            if not utils.is_linux():
                _warning("Crontab editing is only available on Linux.")
            else:
                sched = _ask("schedule (e.g. */5 * * * *)")
                cmd = _ask("command to run")
                ok, msg = scheduler.add_job(sched, cmd)
                (_success if ok else _error)(msg)
        elif choice == "3":
            if not utils.is_linux():
                _warning("Crontab editing is only available on Linux.")
            else:
                idx_str = _ask("job index to remove")
                if idx_str.isdigit():
                    ok, msg = scheduler.remove_job(int(idx_str))
                    (_success if ok else _error)(msg)
                else:
                    _error("Invalid index.")
        _pause()


# 4. User Manager (Silver+)
def users_screen() -> None:
    while True:
        _render_menu(T.get("users_title", "USER MANAGER"), [
            ("1", "List users"),
            ("2", "List groups"),
            ("3", "Lock user account"),
            ("4", "Unlock user account"),
            ("0", "Back"),
        ])
        choice = _ask("users")
        if choice == "0":
            return
        elif choice == "1":
            u_list = users_module.list_users()
            _print_table("User Accounts", ["Username", "UID", "Home", "Locked"],
                         [[u.username, u.uid, u.home, u.locked] for u in u_list])
        elif choice == "2":
            g_list = users_module.list_groups()
            _print_table("System Groups", ["Group Name", "GID", "Members"],
                         [[g.name, g.gid, ", ".join(g.members)] for g in g_list])
        elif choice == "3":
            username = _ask("username to lock")
            if _confirm(f"Are you sure you want to lock '{username}'?", default=False):
                res = users_module.lock_user(username)
                (_success if res.ok else _error)(res.stdout or res.error or "Lock failed.")
        elif choice == "4":
            username = _ask("username to unlock")
            if _confirm(f"Are you sure you want to unlock '{username}'?", default=False):
                res = users_module.unlock_user(username)
                (_success if res.ok else _error)(res.stdout or res.error or "Unlock failed.")
        _pause()


# 5. Docker Center (Gold)
def docker_screen() -> None:
    if not docker_center.is_available():
        _warning(T.get("docker_missing", "Docker is not installed. Redirecting to App Installer..."))
        _pause()
        installer_screen()
        return

    while True:
        _render_menu(T.get("docker_title", "DOCKER CENTER"), [
            ("1", "Running containers"),
            ("2", "All containers"),
            ("3", "Images"),
            ("4", "Container logs"),
            ("5", "Start / Stop / Restart"),
            ("6", "Remove container"),
            ("7", "Remove image"),
            ("8", "System prune"),
            ("0", "Back"),
        ])
        choice = _ask("docker")
        if choice == "0":
            return
        elif choice in ("1", "2"):
            all_c = (choice == "2")
            clist = docker_center.list_containers(all_containers=all_c)
            _print_table("Containers", ["ID", "Image", "Status", "Ports", "Name"],
                         [[c.container_id[:12], c.image, c.status, c.ports, c.name] for c in clist])
        elif choice == "3":
            imgs = docker_center.list_images()
            _print_table("Docker Images", ["Repository", "Tag", "ID", "Size"],
                         [[img.repository, img.tag, img.image_id[:12], img.size] for img in imgs])
        elif choice == "4":
            name = _ask("container name or ID")
            out = docker_center.container_logs(name)
            print("\n" + out[:4000])
        elif choice == "5":
            c_name = _ask("container name or ID")
            _render_menu("Action", [("1", "Start"), ("2", "Stop"), ("3", "Restart")])
            act = _ask("action")
            if act == "1":
                res = docker_center.start_container(c_name)
            elif act == "2":
                res = docker_center.stop_container(c_name)
            elif act == "3":
                res = docker_center.restart_container(c_name)
            else:
                res = None
            if res:
                (_success if res.ok else _error)(res.stdout or res.error or "Done.")
        elif choice == "6":
            name = _ask("container name or ID to remove")
            if _confirm(f"Remove container '{name}'?", default=False):
                res = docker_center.remove_container(name)
                (_success if res.ok else _error)(res.stdout or res.error or "Done.")
        elif choice == "7":
            name = _ask("image repository or ID to remove")
            if _confirm(f"Remove image '{name}'?", default=False):
                res = docker_center.remove_image(name)
                (_success if res.ok else _error)(res.stdout or res.error or "Done.")
        elif choice == "8":
            est = docker_center.prune_estimate()
            print("\n" + est)
            if _confirm("Run docker system prune -f?", default=False):
                res = docker_center.prune()
                (_success if res.ok else _error)(res.stdout or res.error or "Done.")
        _pause()


# 6. Environment Manager (Silver+)
def env_screen() -> None:
    while True:
        _render_menu(T.get("env_title", "ENVIRONMENT MANAGER"), [
            ("1", "List environment variables"),
            ("2", "Add directory to PATH"),
            ("3", "Set variable"),
            ("4", "Remove variable"),
            ("0", "Back"),
        ])
        choice = _ask("env")
        if choice == "0":
            return
        elif choice == "1":
            flt = _ask("filter (leave blank for all)")
            env_vars = env_manager.list_env(flt)
            _print_table("Environment Variables", ["Key", "Value"],
                         [[k, v[:60]] for k, v in env_vars[:50]])
        elif choice == "2":
            path_dir = _ask("directory to add to PATH")
            ok, msg = env_manager.add_to_path(path_dir)
            (_success if ok else _error)(msg)
        elif choice == "3":
            k = _ask("variable key")
            v = _ask("variable value")
            ok, msg = env_manager.set_variable(k, v)
            (_success if ok else _error)(msg)
        elif choice == "4":
            k = _ask("variable key to remove")
            if _confirm(f"Remove variable '{k}'?", default=False):
                ok, msg = env_manager.remove_variable(k)
                (_success if ok else _error)(msg)
        _pause()


# 7. Backup Tool (Gold)
def backup_screen() -> None:
    while True:
        _render_menu(T.get("backup_title", "BACKUP TOOL"), [
            ("1", "Create backup"),
            ("2", "List backups"),
            ("3", "Verify backup checksum"),
            ("4", "Restore backup"),
            ("0", "Back"),
        ])
        choice = _ask("backup")
        if choice == "0":
            return
        elif choice == "1":
            src = _ask("source path to back up")
            dst = _ask("destination folder (default ./backups)") or "./backups"
            size = backup.estimate_size(src)
            _info(f"Estimated size: {utils.human_bytes(size)}")
            if _confirm("Start backup creation?", default=True):
                print(f"  {C.DIM}Archiving...{C.RESET}")
                ok, path = backup.create_backup(src, dst)
                (_success if ok else _error)(f"Backup created: {path}" if ok else path)
        elif choice == "2":
            dst = _ask("backups directory (default ./backups)") or "./backups"
            b_list = backup.list_backups(dst)
            _print_table("Backups", ["Path", "Size", "Date", "Checksum Available"],
                         [[b.path, b.size, b.date, "Yes" if b.checksum_file else "No"] for b in b_list])
        elif choice == "3":
            archive_path = _ask("path to .tar.gz backup archive")
            ok, msg = backup.verify_backup(archive_path)
            (_success if ok else _error)(msg)
        elif choice == "4":
            archive_path = _ask("path to .tar.gz backup archive")
            dest_dir = _ask("destination folder to extract to")
            if _confirm(f"Extract '{archive_path}' to '{dest_dir}'?", default=False):
                ok, msg = backup.restore_backup(archive_path, dest_dir)
                (_success if ok else _error)(msg)
        _pause()


# 8. Port Scanner (Silver+)
def ports_screen() -> None:
    while True:
        _render_menu(T.get("ports_title", "PORT SCANNER (local)"), [
            ("1", "Listening ports"),
            ("2", "Established connections"),
            ("3", "Check specific port"),
            ("0", "Back"),
        ])
        choice = _ask("ports")
        if choice == "0":
            return
        elif choice == "1":
            p_list = ports.get_listening_ports()
            _print_table("Listening Ports (localhost)", ["Port", "Proto", "Local Addr", "PID/Proc"],
                         [[p.port, p.protocol, p.local_addr, f"{p.pid} {p.process}".strip()] for p in p_list])
        elif choice == "2":
            e_list = ports.get_established()
            _print_table("Active Established Connections", ["Port", "Local Addr", "Remote Addr"],
                         [[p.port, p.local_addr, p.remote_addr] for p in e_list])
        elif choice == "3":
            port_str = _ask("port number to check (e.g. 80)")
            if port_str.isdigit():
                p_num = int(port_str)
                is_open = ports.check_port_open(p_num)
                (_success if is_open else _warning)(f"Port {p_num} on localhost is {'OPEN' if is_open else 'CLOSED / filtered'}.")
            else:
                _error("Invalid port number.")
        _pause()


# 9. Git Helper (Silver+)
def git_screen() -> None:
    if not git_helper.is_available():
        _warning(T.get("git_missing", "Git is not installed. Redirecting to App Installer..."))
        _pause()
        installer_screen()
        return

    active_repo: str | None = None

    while True:
        repo_label = active_repo if active_repo else "None selected"
        _render_menu(f"{T.get('git_title', 'GIT HELPER')} [Repo: {repo_label}]", [
            ("1", "Select / Detect repository"),
            ("2", "Status"),
            ("3", "Log"),
            ("4", "Quick commit (add -A & commit)"),
            ("5", "Pull"),
            ("6", "Push"),
            ("7", "Stash / Stash pop"),
            ("0", "Back"),
        ])
        choice = _ask("git")
        if choice == "0":
            return
        elif choice == "1":
            search_path = _ask("search path (default current dir)") or "."
            found_repos = git_helper.detect_repos(search_path)
            if not found_repos:
                _warning("No git repositories found.")
            else:
                _print_table("Found Repositories", ["Index", "Name", "Path"],
                             [[i + 1, r.name, r.path] for i, r in enumerate(found_repos)])
                sel = _ask("select repository index")
                if sel.isdigit() and 1 <= int(sel) <= len(found_repos):
                    active_repo = found_repos[int(sel) - 1].path
                    _success(f"Selected repo: {active_repo}")
                else:
                    _error("Invalid selection.")
        elif choice in ("2", "3", "4", "5", "6", "7") and not active_repo:
            _warning("Please select a repository first (Option 1).")
        elif choice == "2" and active_repo:
            st = git_helper.status(active_repo)
            _info(f"Branch: {st.branch}", title="Git Status")
            print(st.raw if st.raw else "  (working tree clean)")
        elif choice == "3" and active_repo:
            lines_str = _ask("number of commits (default 10)") or "10"
            out = git_helper.log(active_repo, int(lines_str) if lines_str.isdigit() else 10)
            print("\n" + out)
        elif choice == "4" and active_repo:
            diff = git_helper.diff_stat(active_repo)
            print("\n" + diff)
            msg = _ask("commit message")
            if msg and _confirm("Proceed with commit?", default=True):
                res = git_helper.quick_commit(active_repo, msg)
                (_success if res.ok else _error)(res.stdout or res.error or "Commit failed.")
        elif choice == "5" and active_repo:
            if _confirm("Pull from remote?", default=True):
                res = git_helper.pull(active_repo)
                (_success if res.ok else _error)(res.stdout or res.error or "Pull failed.")
        elif choice == "6" and active_repo:
            if _confirm("Push to remote?", default=True):
                res = git_helper.push(active_repo)
                (_success if res.ok else _error)(res.stdout or res.error or "Push failed.")
        elif choice == "7" and active_repo:
            _render_menu("Stash Action", [("1", "Stash changes"), ("2", "Pop stash")])
            act = _ask("choice")
            if act == "1" and _confirm("Stash working tree changes?", default=True):
                res = git_helper.stash(active_repo)
                (_success if res.ok else _error)(res.stdout or res.error or "Failed.")
            elif act == "2" and _confirm("Pop latest stash?", default=True):
                res = git_helper.stash_pop(active_repo)
                (_success if res.ok else _error)(res.stdout or res.error or "Failed.")
        _pause()


# 10. Update Center (Gold)
def update_screen() -> None:
    while True:
        _render_menu(T.get("update_title", "UPDATE CENTER"), [
            ("1", "Full system update (recommended)"),
            ("2", "Step by step"),
            ("3", "Cleanup only"),
            ("4", "Estimate upgradable packages"),
            ("5", "Check for ROOT//X TOOLKIT updates (GitHub)"),
            ("0", "Back"),
        ])
        choice = _ask("update")
        if choice == "0":
            return
        elif choice == "4":
            est = update_center.estimate_upgradable()
            _info(est, title="Upgradable Packages")
        elif choice == "5":
            print(f"\n  {C.CYAN}[*] {T.get('update_downloading', 'Checking for updates on GitHub...')}{C.RESET}")
            has_update, info = self_updater.check_for_updates()
            if has_update and info:
                short_sha = info.get("short_sha", "latest")
                msg = info.get("message", "")
                _warning(f"New update available on GitHub: [{short_sha}] {msg}")
                if _confirm(T.get("update_prompt", "Do you want to update now?"), default=True):
                    ok, err = self_updater.apply_update()
                    if ok:
                        _success(T.get("update_success", "Update installed! Restarting..."))
                        time.sleep(1.2)
                        self_updater.restart_toolkit()
                    else:
                        _error(f"{T.get('update_failed', 'Update failed.')} ({err})")
            else:
                _success(T.get("update_uptodate", "Toolkit is already up to date."))
        elif choice == "1":
            if _confirm("Run full system update & upgrade?", default=False):
                print(f"  {C.DIM}Running updates...{C.RESET}")
                results = update_center.run_all(progress_callback=lambda step: print(f"  {C.CYAN}Step: {step}...{C.RESET}"))
                for r in results:
                    (_success if r.ok else _error)(f"Step '{r.step}': {'OK' if r.ok else r.error}")
        elif choice == "2":
            steps = update_center.get_steps()
            for step in steps:
                _print_command_box(f"STEP: {step.name}", {"Description": step.description, "Command": " ".join(step.command)})
                if _confirm(f"Run step '{step.name}'?", default=True):
                    res = update_center.run_step(step)
                    (_success if res.ok else _error)(f"Result: {'OK' if res.ok else res.error}")
                else:
                    _info("Skipped.")
        elif choice == "3":
            if _confirm("Run package cleanup (autoremove/clean)?", default=True):
                results = update_center.cleanup_only()
                for r in results:
                    (_success if r.ok else _error)(f"Step '{r.step}': {'OK' if r.ok else r.error}")
        _pause()


# 11. Benchmark (Gold)
def benchmark_screen() -> None:
    while True:
        _render_menu(T.get("bench_title", "BENCHMARK"), [
            ("1", "Run all benchmarks"),
            ("2", "CPU only"),
            ("3", "RAM only"),
            ("4", "Disk only"),
            ("5", "View previous results"),
            ("0", "Back"),
        ])
        choice = _ask("benchmark")
        if choice == "0":
            return
        elif choice == "1":
            print(f"  {C.DIM}Running all system benchmarks...{C.RESET}")
            results = benchmark.run_all_benchmarks()
            for r in results:
                _success(f"{r.name}: {r.score} {r.unit} ({r.duration_sec}s)")
            path = benchmark.save_results(results)
            _info(f"Results saved to: {path}")
        elif choice == "2":
            print(f"  {C.DIM}Running CPU benchmark...{C.RESET}")
            r1 = benchmark.bench_cpu_single()
            r2 = benchmark.bench_cpu_multi()
            _success(f"{r1.name}: {r1.score} {r1.unit}")
            _success(f"{r2.name}: {r2.score} {r2.unit}")
        elif choice == "3":
            print(f"  {C.DIM}Running RAM benchmark...{C.RESET}")
            r = benchmark.bench_ram()
            _success(f"{r.name}: {r.score} {r.unit}")
        elif choice == "4":
            print(f"  {C.DIM}Running Disk benchmark...{C.RESET}")
            r = benchmark.bench_disk()
            _success(f"{r.name}: {r.score} {r.unit}")
        elif choice == "5":
            prev = benchmark.list_previous_results()
            if not prev:
                _warning("No previous benchmark files found.")
            else:
                _print_table("Previous Benchmark Files", ["Path"], [[p] for p in prev])
        _pause()


# 12. Debloater & Telemetry Stripper
def debloater_screen() -> None:
    from rootx.ram_cleaner import is_admin
    is_adm = is_admin()
    saved_token = get_saved_token()
    result_lic = verify_token(saved_token) if saved_token else LicenseResult(False)
    active_tier = result_lic.tier if result_lic.valid else "bronze"

    while True:
        _render_menu(T.get("debloat_title", "DEBLOATER & TELEMETRY STRIPPER"), [
            ("1", "View telemetry/bloat services"),
            ("2", "Run telemetry stripper"),
            ("0", "Back"),
        ])
        choice = _ask("debloater")
        if choice == "0":
            return
        elif choice == "1":
            if sys.platform == "win32":
                services_list = debloater.get_windows_telemetry_services()
                _print_table("Windows Telemetry Services", ["Service Name", "Display Name"], [[s["name"], s["display"]] for s in services_list])
            else:
                services_list = debloater.get_linux_bloat_services()
                _print_table("Linux Bloat Services", ["Service Name", "Description"], [[s["name"], s["display"]] for s in services_list])
        elif choice == "2":
            if not is_adm:
                _warning("Running without Administrator/root privileges. Some services may fail to disable.")
            if _confirm("Disable telemetry and trackers?"):
                _info("Applying tweaks...")
                res = debloater.run_debloat(active_tier)
                for s in res.success:
                    _success(s)
                for f in res.failed:
                    _error(f"Failed: {f}")
                for sk in res.skipped:
                    _info(f"Skipped: {sk}")
        _pause()


# 13. Autostart & Persistence Inspector
def autostart_screen() -> None:
    while True:
        _render_menu(T.get("autostart_title", "AUTOSTART & PERSISTENCE INSPECTOR"), [
            ("1", "Scan autostart locations"),
            ("2", "Remove autostart entry"),
            ("0", "Back"),
        ])
        choice = _ask("autostart")
        if choice == "0":
            return
        elif choice == "1":
            _info("Scanning persistence locations...")
            entries = autostart.scan_all()
            if not entries:
                _info("No autostart entries detected.")
            else:
                rows = []
                for e in entries:
                    susp = f"{C.RED}SUSPICIOUS{C.RESET}" if e.suspicious else "Safe"
                    rows.append([e.source, e.name, e.command[:50], susp])
                _print_table("Autostart / Persistence Entries", ["Source", "Name", "Command", "Status"], rows)
        elif choice == "2":
            name = _ask("Enter the exact name of the entry to remove")
            if not name:
                continue
            if _confirm(f"Are you sure you want to remove '{name}'?"):
                if sys.platform == "win32":
                    ok = autostart.remove_windows_run_entry(name)
                else:
                    ok = autostart.remove_linux_xdg_entry(name)
                if ok:
                    _success(f"Successfully removed entry: {name}")
                else:
                    _error(f"Failed to remove entry: {name}")
        _pause()


# 14. RAM & Cache Purger
def ram_cleaner_screen() -> None:
    while True:
        _render_menu(T.get("ram_cleaner_title", "RAM & CACHE PURGER"), [
            ("1", "View current RAM info"),
            ("2", "Run RAM & Cache purge"),
            ("0", "Back"),
        ])
        choice = _ask("ram_cleaner")
        if choice == "0":
            return
        elif choice == "1":
            info = ram_cleaner.get_ram_info()
            _print_command_box("RAM Memory Status", {
                "Total RAM": f"{info.total_mb} MB",
                "Available RAM": f"{info.available_mb} MB",
                "Used RAM": f"{info.used_mb} MB ({info.percent}%)",
            })
        elif choice == "2":
            _info("Purging system memory and caches...")
            before, after, msg = ram_cleaner.clean_ram()
            _info(f"Status: {msg}")
            _success(f"RAM before: {before.used_mb} MB ({before.percent}%) -> RAM after: {after.used_mb} MB ({after.percent}%)")
        _pause()


# 15. Live TUI Resource Monitor
def live_monitor_screen() -> None:
    _info("Starting Live TUI Monitor. Press Ctrl+C to exit.")
    time.sleep(1)
    live_monitor.run_live_monitor()


# 16. Disk Health & SMART Monitor
def smart_disk_screen() -> None:
    import sys
    from pathlib import Path
    if sys.platform != "win32" and not smart_disk.is_smartctl_available():
        _warning("smartctl utility is not installed. Redirecting to App Installer...")
        _pause()
        installer_screen()
        return

    _info("Reading disk health info...")
    disks = smart_disk.get_all_disk_health()
    if not disks:
        _warning("No physical disks found or failed to query S.M.A.R.T.")
    else:
        for d in disks:
            _print_command_box(f"Device: {d.device} ({d.interface})", {
                "Model": d.model,
                "Health Status": f"{C.GREEN}{d.health}{C.RESET}" if d.health == "PASSED" else f"{C.RED}{d.health}{C.RESET}",
                "Temperature": f"{d.temperature_c} C" if d.temperature_c is not None else "N/A",
                "Power On Hours": f"{d.power_on_hours} hours" if d.power_on_hours is not None else "N/A",
                "Total Bytes Written (TBW)": f"{d.tbw_tb} TB" if d.tbw_tb is not None else "N/A",
                "Size": f"{d.size_gb} GB" if d.size_gb is not None else "N/A",
                "Reallocated Sectors": d.reallocated_sectors if d.reallocated_sectors is not None else "N/A",
            })
    _pause()


# 17. HTTP File Share & QR Code
def fileshare_screen() -> None:
    from pathlib import Path
    while True:
        _render_menu(T.get("fileshare_title", "HTTP FILE SHARE & QR CODE"), [
            ("1", "Share a file"),
            ("2", "Share a directory"),
            ("0", "Back"),
        ])
        choice = _ask("fileshare")
        if choice == "0":
            return
        
        path_str = _ask("Enter the absolute path to share")
        if not path_str:
            continue
        
        path = Path(path_str)
        if not path.exists():
            _error("Path does not exist.")
            _pause()
            continue

        if choice == "1" and not path.is_file():
            _error("Specified path is not a file.")
            _pause()
            continue
        elif choice == "2" and not path.is_dir():
            _error("Specified path is not a directory.")
            _pause()
            continue

        try:
            _info(f"Starting server for path: {path}")
            server = fileshare.share_path(str(path))
            url = server.get_share_url()
            
            _success(f"Server is running!")
            _info(f"Connect to: {url}")
            print()
            print(fileshare.render_qr_ascii(url))
            print()
            
            _info("Press Enter to stop the file sharing server.")
            input()
            server.stop()
            _success("Server stopped.")
        except Exception as e:
            _error(f"Failed to start server: {e}")
        _pause()


# 18. SSL/TLS Certificate & DNS Inspector
def ssl_inspector_screen() -> None:
    while True:
        _render_menu(T.get("ssl_inspector_title", "SSL/TLS & DOMAIN INSPECTOR"), [
            ("1", "Inspect domain (SSL + DNS)"),
            ("0", "Back"),
        ])
        choice = _ask("ssl")
        if choice == "0":
            return
        elif choice == "1":
            domain = _ask("Enter domain name (e.g. google.com)")
            if not domain:
                continue
            
            _info(f"Inspecting domain: {domain}...")
            ssl_info, dns_info = ssl_inspector.check_domain(domain)
            
            if ssl_info.error:
                _error(f"SSL Inspection error: {ssl_info.error}")
            else:
                status = f"{C.GREEN}VALID{C.RESET}" if ssl_info.valid else f"{C.RED}INVALID{C.RESET}"
                _print_command_box(f"SSL Certificate Status: {ssl_info.domain}", {
                    "Status": status,
                    "Issuer": ssl_info.issuer,
                    "Subject": ssl_info.subject,
                    "Expires At": ssl_info.expires_at,
                    "Days Remaining": f"{ssl_info.days_remaining} days" if ssl_info.days_remaining is not None else "N/A",
                    "Protocol": ssl_info.protocol,
                })
            
            if dns_info.error:
                _error(f"DNS query error: {dns_info.error}")
            else:
                _print_command_box(f"DNS Records: {dns_info.domain}", {
                    "A Records": ", ".join(dns_info.a_records) if dns_info.a_records else "None",
                    "AAAA Records": ", ".join(dns_info.aaaa_records) if dns_info.aaaa_records else "None",
                    "MX Records": ", ".join(dns_info.mx_records) if dns_info.mx_records else "None",
                    "NS Records": ", ".join(dns_info.ns_records) if dns_info.ns_records else "None",
                    "TXT Records": ", ".join(dns_info.txt_records) if dns_info.txt_records else "None",
                })
        _pause()


# 19. Hash Calculator & Password Generator
def hash_tool_screen() -> None:
    import os
    while True:
        _render_menu(T.get("hash_tool_title", "HASH & PASSWORD GENERATOR"), [
            ("1", "Compute file hashes"),
            ("2", "Generate secure password"),
            ("3", "Generate secure API key / UUID"),
            ("0", "Back"),
        ])
        choice = _ask("hash_tool")
        if choice == "0":
            return
        elif choice == "1":
            path = _ask("Enter absolute file path")
            if not path or not os.path.exists(path):
                _error("Invalid file path.")
                _pause()
                continue
            compare = _ask("Enter expected hash to compare (optional, default: none)")
            _info("Computing hashes...")
            results = hash_tool.hash_file(path, compare_with=compare if compare else None)
            for algo, r in results.items():
                match_str = ""
                if r.match is True:
                    match_str = f" {C.GREEN}(MATCHES EXPECTED){C.RESET}"
                elif r.match is False:
                    match_str = f" {C.RED}(MISMATCH!){C.RESET}"
                print(f"  {C.BOLD}{algo.upper()}:{C.RESET} {r.value}{match_str}")
        elif choice == "2":
            try:
                length = int(_ask("Enter password length (default: 24)"))
            except ValueError:
                length = 24
            
            pwd_res = hash_tool.generate_password(length)
            _print_command_box("Generated Password", {
                "Password": f"{C.BOLD}{C.GREEN}{pwd_res.password}{C.RESET}",
                "Length": pwd_res.length,
                "Charset": pwd_res.charset,
                "Entropy (bits)": pwd_res.entropy_bits,
            })
        elif choice == "3":
            key = hash_tool.generate_api_key(64)
            uid = hash_tool.generate_uuid()
            _print_command_box("Generated Keys", {
                "API Key (64-char hex)": key,
                "UUID v4": uid,
            })
        _pause()


# Theme Selector Screen
def theme_selector_screen() -> None:
    while True:
        opts = [(k, v["name"]) for k, v in themes.THEMES.items()]
        opts.append(("0", "Back"))
        _render_menu(T.get("theme_selector_title", "SELECT COLOR THEME"), opts)
        
        choice = _ask("theme")
        if choice == "0":
            return
        elif choice in themes.THEMES:
            themes.save_theme(choice)
            _success(f"Theme successfully updated to: {themes.THEMES[choice]['name']}")
            break
        else:
            _error("Unknown theme ID.")
    _pause()


# Web Panel Screen
def web_panel_screen() -> None:
    saved_token = get_saved_token()
    result_lic = verify_token(saved_token) if saved_token else LicenseResult(False)
    active_tier = result_lic.tier if result_lic.valid else "bronze"

    _info("Starting localhost Web Panel server...")
    try:
        server = webpanel.WebPanelServer(port=7070, tier=active_tier)
        url_with_token = server.start()
        
        _success("Web Panel Server is running on http://127.0.0.1:7070")
        _info(f"One-time Session Token: {server.token}")
        _info("Opening browser automatically...")
        
        import webbrowser
        webbrowser.open(url_with_token)
        
        _info("Web panel is running in the background. Press Enter here to stop the server.")
        input()
        server.stop()
        _success("Web Panel Server stopped.")
    except Exception as e:
        _error(f"Failed to start Web Panel: {e}")
    _pause()


# ─── Main menu with tier gating ────────────────────────────────────────────

MAIN_MENU_OPTIONS = [
    ("1", "ROOT//X DOCTOR", "bronze"),
    ("2", "APP INSTALLER", "bronze"),
    ("3", "NETWORK CENTER", "bronze"),
    ("4", "DISK CENTER", "bronze"),
    ("5", "PROCESS CENTER", "bronze"),
    ("6", "SERVICE MANAGER", "bronze"),
    ("7", "PACKAGE MANAGER", "bronze"),
    ("8", "SYSTEM INFORMATION", "bronze"),
    ("9", "DIAGNOSTIC REPORT", "bronze"),
    ("10", "FIREWALL CENTER", "silver"),
    ("11", "LOG VIEWER", "silver"),
    ("12", "TASK SCHEDULER", "silver"),
    ("13", "USER MANAGER", "silver"),
    ("14", "DOCKER CENTER", "gold"),
    ("15", "ENVIRONMENT MANAGER", "silver"),
    ("16", "BACKUP TOOL", "gold"),
    ("17", "PORT SCANNER (local)", "silver"),
    ("18", "GIT HELPER", "silver"),
    ("19", "UPDATE CENTER", "gold"),
    ("20", "BENCHMARK", "gold"),
    ("21", "DEBLOATER & TELEMETRY STRIPPER", "silver"),
    ("22", "AUTOSTART & PERSISTENCE INSPECTOR", "silver"),
    ("23", "RAM & CACHE PURGER", "silver"),
    ("24", "LIVE TUI RESOURCE MONITOR", "gold"),
    ("25", "DISK HEALTH & S.M.A.R.T. MONITOR", "gold"),
    ("26", "HTTP FILE SHARE & QR CODE", "silver"),
    ("27", "SSL/TLS & DOMAIN INSPECTOR", "silver"),
    ("28", "HASH & PASSWORD GENERATOR", "bronze"),
]


def _get_menu_label(key: str, default_label: str) -> str:
    mapping = {
        "1": "doctor_title",
        "2": "installer_title",
        "3": "network_title",
        "4": "disk_title",
        "5": "process_title",
        "6": "services_title",
        "7": "package_manager_title",
        "8": "system_info_title",
        "9": "report_title",
        "10": "fw_title",
        "11": "logs_title",
        "12": "sched_title",
        "13": "users_title",
        "14": "docker_title",
        "15": "env_title",
        "16": "backup_title",
        "17": "ports_title",
        "18": "git_title",
        "19": "update_title",
        "20": "bench_title",
        "21": "debloat_title",
        "22": "autostart_title",
        "23": "ram_cleaner_title",
        "24": "live_monitor_title",
        "25": "smart_disk_title",
        "26": "fileshare_title",
        "27": "ssl_inspector_title",
        "28": "hash_tool_title",
    }
    tkey = mapping.get(key)
    if tkey:
        return T.get(tkey, default_label)
    return default_label


def _main_menu() -> None:
    """Toolkit menu after activation."""
    while True:
        _clear()
        print(BANNER)
        print(f"  {C.DIM}  {utils.os_name()} · {utils.detect_architecture()}{C.RESET}")

        saved = get_saved_token()
        result = verify_token(saved) if saved else LicenseResult(False)

        if not result.valid:
            print(f"\n  {C.RED}✗ {T.get('activate_retry', 'License expired or revoked. Please reactivate.')}{C.RESET}\n")
            deactivate()
            input(f"  {C.DIM}Press Enter...{C.RESET}")
            return

        if result.offline:
            print(f"  {C.YELLOW}  {T.get('menu_offline', '[!] Offline mode — cache valid for 7 days')}{C.RESET}")

        tier_str = result.tier.upper() if result.valid else "NONE"
        print(f"  {C.CYAN}  Tier level: {C.BOLD}{tier_str}{C.RESET}")

        print(f"\n  {C.YELLOW}{'━' * 50}{C.RESET}")
        print(f"  {C.BOLD}{C.WHITE}  {T.get('menu_title', 'MAIN MENU')}{C.RESET}")
        print(f"  {C.YELLOW}{'━' * 50}{C.RESET}\n")

        for key, label, required_tier in MAIN_MENU_OPTIONS:
            display_label = _get_menu_label(key, label)
            if has_tier(result, required_tier):
                print(f"  {C.CYAN}  [{key}]{C.RESET}  {display_label}")
            else:
                locked_label = T.get("tier_locked", "Locked")
                print(f"  {C.DIM}  [{key}]  {display_label}  [ Tier {required_tier.capitalize()} {locked_label} ]{C.RESET}")
        print()
        print(f"  {C.DIM}  [K]{C.RESET}  {C.DIM}Change language / Wybierz język{C.RESET}")
        print(f"  {C.DIM}  [T]{C.RESET}  {C.DIM}{T.get('theme_selector_title', 'Select Theme')}{C.RESET}")
        print(f"  {C.DIM}  [W]{C.RESET}  {C.DIM}{T.get('web_panel_title', 'Web Panel')}{C.RESET}")
        print(f"  {C.DIM}  [L]{C.RESET}  {C.DIM}Log out (remove local license){C.RESET}")
        print(f"  {C.DIM}  [Q]{C.RESET}  {C.DIM}Quit{C.RESET}")
        print(f"\n  {C.YELLOW}{'━' * 50}{C.RESET}")

        try:
            choice = input(f"\n  {C.CYAN}Choose an option:{C.RESET} ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        try:
            if choice == "q":
                break
            elif choice == "k":
                _language_picker_screen()
                continue
            elif choice == "t":
                theme_selector_screen()
                continue
            elif choice == "w":
                web_panel_screen()
                continue
            elif choice == "l":
                deactivate()
                print(f"\n  {C.GREEN}✓ {T.get('logout_success', 'Logged out.')}{C.RESET}")
                input(f"  {C.DIM}Press Enter...{C.RESET}")
                return

            option_entry = next((opt for opt in MAIN_MENU_OPTIONS if opt[0] == choice), None)
            if option_entry:
                _, _, req_tier = option_entry
                if not has_tier(result, req_tier):
                    _warning(f"This feature requires {req_tier.capitalize()} tier or higher.")
                    _pause()
                    continue

            if choice == "1":
                doctor_screen()
            elif choice == "2":
                installer_screen()
            elif choice == "3":
                network_screen()
            elif choice == "4":
                disk_screen()
            elif choice == "5":
                process_screen()
            elif choice == "6":
                service_screen()
            elif choice == "7":
                package_manager_screen()
            elif choice == "8":
                system_info_screen()
            elif choice == "9":
                report_screen()
            elif choice == "10":
                firewall_screen()
            elif choice == "11":
                logs_screen()
            elif choice == "12":
                scheduler_screen()
            elif choice == "13":
                users_screen()
            elif choice == "14":
                docker_screen()
            elif choice == "15":
                env_screen()
            elif choice == "16":
                backup_screen()
            elif choice == "17":
                ports_screen()
            elif choice == "18":
                git_screen()
            elif choice == "19":
                update_screen()
            elif choice == "20":
                benchmark_screen()
            elif choice == "21":
                debloater_screen()
            elif choice == "22":
                autostart_screen()
            elif choice == "23":
                ram_cleaner_screen()
            elif choice == "24":
                live_monitor_screen()
            elif choice == "25":
                smart_disk_screen()
            elif choice == "26":
                fileshare_screen()
            elif choice == "27":
                ssl_inspector_screen()
            elif choice == "28":
                hash_tool_screen()
            else:
                print(f"  {C.RED}✗ {T.get('unknown_option', 'Unknown option.')}{C.RESET}")
                input(f"  {C.DIM}Press Enter...{C.RESET}")
        except (KeyboardInterrupt, EOFError):
            print()
            _warning(T.get("op_cancelled", "Operation cancelled."))
        except Exception as exc:
            _error(f"{T.get('unexpected_error', 'An unexpected error occurred')}: {exc}")
            _pause()


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    _enable_ansi_windows()

    # Show language picker on first launch (if no saved language choice exists)
    if not has_saved_language():
        _language_picker_screen()

    # Check for Toolkit updates from GitHub on startup
    try:
        if self_updater.check_and_prompt_update(C, T):
            return
    except Exception:
        pass

    # Perform startup online license verification with feedback
    saved = get_saved_token()
    if saved:
        _clear()
        print(BANNER)
        print(f"  {C.CYAN}Verifying license online...{C.RESET}")
        result = verify_token(saved)
        if result.valid:
            mode_str = " [offline cache]" if result.offline else " [online]"
            print(f"  {C.GREEN}✓ License verified: {result.tier.upper()} Tier{mode_str}{C.RESET}\n")
        else:
            print(f"  {C.RED}✗ License check failed: {result.reason}{C.RESET}\n")
            deactivate()
            input(f"  {C.DIM}Press Enter to reactivate...{C.RESET}")

    while True:
        if is_activated():
            _main_menu()
            if not is_activated():
                continue
            break
        else:
            success = _activation_screen()
            if not success:
                sys.exit(0)
            _main_menu()
            if not is_activated():
                continue
            break
