"""
rootx.firewall
==============
Firewall management center.
Platforms: Linux (ufw / firewalld / iptables) and Windows (netsh / PowerShell).
macOS: not supported — returns early.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from . import utils


@dataclass
class FirewallRule:
    rule_id: str
    direction: str   # "in" | "out" | "both"
    action: str      # "allow" | "deny" | "reject"
    port: str        # "22" | "any"
    protocol: str    # "tcp" | "udp" | "any"
    source: str      # "anywhere" | IP
    description: str = ""


@dataclass
class FirewallStatus:
    enabled: bool
    backend: str       # "ufw" | "firewalld" | "iptables" | "windows" | "none"
    profile: str = ""  # Windows: "Domain" / "Private" / "Public"
    details: str = ""


def _detect_backend() -> str:
    """Detect available firewall backend. Returns 'ufw'|'firewalld'|'iptables'|'windows'|'none'."""
    if utils.is_windows():
        return "windows"
    if utils.command_exists("ufw"):
        return "ufw"
    if utils.command_exists("firewall-cmd"):
        return "firewalld"
    if utils.command_exists("iptables"):
        return "iptables"
    return "none"


def get_status() -> FirewallStatus:
    """Get firewall status and backend info."""
    backend = _detect_backend()
    if backend == "ufw":
        result = utils.run(["ufw", "status"], timeout=10)
        enabled = "active" in result.stdout.lower()
        return FirewallStatus(enabled=enabled, backend="ufw", details=result.stdout)
    elif backend == "firewalld":
        result = utils.run(["firewall-cmd", "--state"], timeout=10)
        enabled = result.ok and "running" in result.stdout.lower()
        return FirewallStatus(enabled=enabled, backend="firewalld", details=result.stdout)
    elif backend == "iptables":
        result = utils.run(["iptables", "-L", "-n"], timeout=10)
        return FirewallStatus(enabled=True, backend="iptables", details=result.stdout[:500])
    elif backend == "windows":
        result = utils.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-NetFirewallProfile | Select-Object Name,Enabled | Format-Table -AutoSize",
            ],
            timeout=15,
        )
        enabled = "True" in result.stdout
        return FirewallStatus(enabled=enabled, backend="windows", details=result.stdout)
    return FirewallStatus(enabled=False, backend="none", details="No supported firewall backend detected.")


def list_rules() -> List[FirewallRule]:
    """Return active firewall rules as a list."""
    backend = _detect_backend()
    rules: List[FirewallRule] = []
    if backend == "ufw":
        result = utils.run(["ufw", "status", "numbered"], timeout=10)
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("["):
                m = re.match(r"\[\s*(\d+)\]\s+(\S+)\s+(\w+)\s+(\w+)\s+(.*)", line)
                if m:
                    rules.append(
                        FirewallRule(
                            rule_id=m.group(1),
                            port=m.group(2),
                            action=m.group(3).lower(),
                            direction=m.group(4).lower(),
                            source=m.group(5).strip(),
                            protocol="any",
                        )
                    )
    elif backend == "windows":
        result = utils.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-NetFirewallRule | Where-Object {$_.Enabled -eq 'True'} | Select-Object DisplayName,Direction,Action,Protocol | Format-Table -AutoSize",
            ],
            timeout=20,
        )
        lines = result.stdout.splitlines()
        if len(lines) > 3:
            for i, line in enumerate(lines[3:], 1):
                parts = line.split()
                if len(parts) >= 3:
                    rules.append(
                        FirewallRule(
                            rule_id=str(i),
                            port="any",
                            protocol="any",
                            action=parts[-1].lower(),
                            direction=parts[-2].lower(),
                            source="any",
                            description=" ".join(parts[:-2]),
                        )
                    )
    return rules


def add_rule(port: str, proto: str, action: str, direction: str = "in") -> Dict[str, Any]:
    """Build add-rule command dict. Never executes — returns command for CLI to confirm."""
    backend = _detect_backend()
    if backend == "ufw":
        cmd = ["ufw", action, direction, "proto", proto, "to", "any", "port", port]
    elif backend == "firewalld":
        zone_arg = f"--add-port={port}/{proto}" if action == "allow" else f"--remove-port={port}/{proto}"
        cmd = ["firewall-cmd", "--permanent", zone_arg]
    elif backend == "windows":
        dir_win = "Inbound" if direction == "in" else "Outbound"
        act_win = "Allow" if action == "allow" else "Block"
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"New-NetFirewallRule -DisplayName 'RootX-{port}' -Direction {dir_win} -LocalPort {port} -Protocol {proto.upper()} -Action {act_win}",
        ]
    else:
        return {"error": "No supported firewall backend detected.", "command": []}
    return {"command": cmd, "display": " ".join(cmd), "backend": backend}


def remove_rule(rule_id: str) -> Dict[str, Any]:
    """Build remove-rule command dict. Never executes."""
    backend = _detect_backend()
    if backend == "ufw":
        cmd = ["ufw", "delete", rule_id]
    elif backend == "windows":
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Remove-NetFirewallRule -DisplayName '{rule_id}'",
        ]
    else:
        return {"error": "Remove not supported for this backend.", "command": []}
    return {"command": cmd, "display": " ".join(cmd), "backend": backend}


def set_enabled(enable: bool) -> Dict[str, Any]:
    """Build enable/disable firewall command dict. Never executes."""
    backend = _detect_backend()
    if backend == "ufw":
        cmd = ["ufw", "enable" if enable else "disable"]
    elif backend == "firewalld":
        svc = "start" if enable else "stop"
        cmd = ["systemctl", svc, "firewalld"]
    elif backend == "windows":
        val = "True" if enable else "False"
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Set-NetFirewallProfile -All -Enabled {val}",
        ]
    else:
        return {"error": "No supported firewall backend detected.", "command": []}
    return {"command": cmd, "display": " ".join(cmd), "backend": backend}
