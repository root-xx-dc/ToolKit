"""
rootx.network
=============
Network information and diagnostics: interfaces, local IP, gateway, DNS,
connectivity checks, active connections, traceroute (if available),
and public IP as an explicit opt-in. Nothing here performs scanning.

Cross-platform: interface/IP discovery uses `psutil` where possible; ping,
traceroute and gateway discovery fall back to the right native command per
OS (ping/tracert on Windows, ping/traceroute on macOS & Linux).
"""

from __future__ import annotations

import re
import socket
from dataclasses import dataclass
from typing import List, Optional

from . import utils

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None


@dataclass
class NetworkDoctorResult:
    interface_ok: Optional[bool] = None
    ip_ok: Optional[bool] = None
    gateway_ok: Optional[bool] = None
    dns_ok: Optional[bool] = None
    internet_ok: Optional[bool] = None
    interface_name: str = "N/A"
    local_ip: str = "N/A"
    gateway_ip: str = "N/A"
    suggestion: Optional[str] = None


def get_interfaces() -> List[str]:
    if psutil is not None:
        try:
            stats = psutil.net_if_stats()
            up = [name for name, s in stats.items() if s.isup and name.lower() not in ("lo", "loopback")]
            if up:
                return up
            return [name for name in stats.keys() if name.lower() not in ("lo", "loopback")]
        except Exception:
            pass
    return []


def get_local_ip() -> str:
    if psutil is not None:
        try:
            for name, addrs in psutil.net_if_addrs().items():
                if name.lower() in ("lo", "loopback"):
                    continue
                for addr in addrs:
                    if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                        return addr.address
        except Exception:
            pass
    # Fallback: socket trick (no packets are actually sent, UDP connect only sets up routing)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(1)
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        return "N/A"


def get_gateway() -> str:
    try:
        if utils.is_linux():
            result = utils.run(["ip", "route", "show", "default"], timeout=5)
            if result.ok and result.stdout:
                match = re.search(r"default via (\d+\.\d+\.\d+\.\d+)", result.stdout)
                if match:
                    return match.group(1)
        elif utils.is_macos():
            result = utils.run(["route", "-n", "get", "default"], timeout=5)
            if result.ok and result.stdout:
                match = re.search(r"gateway:\s*(\d+\.\d+\.\d+\.\d+)", result.stdout)
                if match:
                    return match.group(1)
        elif utils.is_windows():
            result = utils.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object -First 1 -ExpandProperty NextHop)"],
                timeout=10,
            )
            if result.ok and result.stdout:
                candidate = result.stdout.strip()
                if re.match(r"^\d+\.\d+\.\d+\.\d+$", candidate):
                    return candidate
    except Exception:
        pass
    return "N/A"


def get_dns_servers() -> List[str]:
    try:
        if utils.is_linux() or utils.is_macos():
            content = utils.safe_read_file("/etc/resolv.conf")
            servers = []
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("nameserver"):
                    parts = line.split()
                    if len(parts) >= 2:
                        servers.append(parts[1])
            if servers:
                return servers
        if utils.is_windows():
            result = utils.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-DnsClientServerAddress -AddressFamily IPv4 | "
                 "Where-Object {$_.ServerAddresses.Count -gt 0} | "
                 "Select-Object -First 1 -ExpandProperty ServerAddresses) -join ','"],
                timeout=10,
            )
            if result.ok and result.stdout:
                return [s for s in result.stdout.strip().split(",") if s]
    except Exception:
        pass
    return []


def ping_host(host: str, count: int = 2, timeout: int = 5) -> bool:
    if utils.is_windows():
        result = utils.run(["ping", "-n", str(count), "-w", "2000", host], timeout=timeout)
    else:
        result = utils.run(["ping", "-c", str(count), "-W", "2", host], timeout=timeout)
    return result.ok


def dns_lookup(host: str) -> Optional[str]:
    try:
        return socket.gethostbyname(host)
    except Exception:
        return None


def get_active_connections(limit: int = 20) -> List[str]:
    if psutil is not None:
        try:
            conns = psutil.net_connections(kind="inet")
            lines = []
            for c in conns[:limit]:
                laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "-"
                raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "-"
                lines.append(f"{c.status:<12} {laddr:<22} -> {raddr:<22} pid={c.pid}")
            if lines:
                return lines
        except Exception:
            pass
    # Fallback to native tools if psutil lacks permission
    if utils.is_windows():
        result = utils.run(["netstat", "-ano"], timeout=5, check_exists=True)
    else:
        result = utils.run(["ss", "-tunp"], timeout=5, check_exists=True)
        if not result.ok:
            result = utils.run(["netstat", "-tunp"], timeout=5, check_exists=True)
    if result.ok and result.stdout:
        return result.stdout.splitlines()[:limit]
    return []


def traceroute(host: str = "8.8.8.8") -> Optional[str]:
    if utils.is_windows():
        if not utils.command_exists("tracert"):
            return None
        result = utils.run(["tracert", "-h", "10", host], timeout=20)
        return result.stdout if result.ok else None
    if not utils.command_exists("traceroute"):
        return None
    result = utils.run(["traceroute", "-m", "10", host], timeout=15)
    return result.stdout if result.ok else None


def get_public_ip() -> Optional[str]:
    """Opt-in only: makes an outbound request. Caller must ask user first."""
    try:
        import urllib.request
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as resp:
            candidate = resp.read().decode("utf-8", errors="ignore").strip()
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", candidate):
                return candidate
    except Exception:
        pass
    return None


def network_doctor() -> NetworkDoctorResult:
    """Run the safe, read-only Network Doctor sequence."""
    result = NetworkDoctorResult()

    interfaces = get_interfaces()
    result.interface_ok = len(interfaces) > 0
    result.interface_name = interfaces[0] if interfaces else "N/A"

    local_ip = get_local_ip()
    result.local_ip = local_ip
    result.ip_ok = local_ip != "N/A"

    gateway = get_gateway()
    result.gateway_ip = gateway
    if gateway != "N/A":
        result.gateway_ok = ping_host(gateway, count=1, timeout=4)
    else:
        result.gateway_ok = False

    dns_servers = get_dns_servers()
    if dns_servers:
        result.dns_ok = dns_lookup("google.com") is not None
    else:
        result.dns_ok = dns_lookup("google.com") is not None  # some OSes hide resolver config

    result.internet_ok = ping_host("1.1.1.1", count=1, timeout=4)

    if not result.interface_ok:
        result.suggestion = "No active network interface detected. Check physical/virtual adapter and cabling."
    elif not result.gateway_ok:
        result.suggestion = "Gateway is unreachable. Check router connectivity or restart the network service."
    elif not result.dns_ok:
        result.suggestion = "DNS resolution failed. Consider switching to a public DNS (e.g. 1.1.1.1 / 8.8.8.8)."
    elif not result.internet_ok:
        result.suggestion = "Local network looks fine but the internet is unreachable. Check your ISP connection."
    else:
        result.suggestion = None

    return result
