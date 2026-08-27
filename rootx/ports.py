"""
rootx.ports
===========
Local port scanner. Only ever touches localhost/127.0.0.1.
No remote scanning. Uses ss/netstat + socket.connect.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import List

from . import utils


@dataclass
class PortInfo:
    port: int
    protocol: str   # tcp | udp
    state: str      # LISTEN | ESTABLISHED | etc.
    local_addr: str
    remote_addr: str
    pid: str
    process: str


def get_listening_ports() -> List[PortInfo]:
    """Get listening ports with owning process."""
    ports: List[PortInfo] = []
    if utils.is_linux():
        if utils.command_exists("ss"):
            result = utils.run(["ss", "-tlnp"], timeout=10)
            for line in result.stdout.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 5:
                    local = parts[4] if len(parts) > 4 else ""
                    port_str = local.rsplit(":", 1)[-1] if ":" in local else "0"
                    try:
                        port_num = int(port_str)
                    except ValueError:
                        port_num = 0
                    process_info = parts[-1] if "users:" in line else ""
                    ports.append(
                        PortInfo(
                            port=port_num,
                            protocol="tcp",
                            state="LISTEN",
                            local_addr=local,
                            remote_addr="",
                            pid="",
                            process=process_info,
                        )
                    )
        elif utils.command_exists("netstat"):
            result = utils.run(["netstat", "-tlnp"], timeout=10)
            for line in result.stdout.splitlines()[2:]:
                parts = line.split()
                if len(parts) >= 4 and parts[0] in ("tcp", "tcp6"):
                    local = parts[3]
                    port_str = local.rsplit(":", 1)[-1]
                    try:
                        port_num = int(port_str)
                    except ValueError:
                        port_num = 0
                    pid_proc = parts[-1] if "/" in parts[-1] else ""
                    pid, _, proc = pid_proc.partition("/")
                    ports.append(
                        PortInfo(
                            port=port_num,
                            protocol="tcp",
                            state="LISTEN",
                            local_addr=local,
                            remote_addr="",
                            pid=pid,
                            process=proc,
                        )
                    )
    elif utils.is_windows():
        result = utils.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-NetTCPConnection -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess | Format-Table -AutoSize",
            ],
            timeout=15,
        )
        lines = result.stdout.splitlines()
        if len(lines) > 3:
            for line in lines[3:]:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        port_num = int(parts[1])
                    except ValueError:
                        port_num = 0
                    pid = parts[2] if len(parts) > 2 else ""
                    ports.append(
                        PortInfo(
                            port=port_num,
                            protocol="tcp",
                            state="LISTEN",
                            local_addr=parts[0],
                            remote_addr="",
                            pid=pid,
                            process="",
                        )
                    )
    return sorted(ports, key=lambda p: p.port)


def get_established() -> List[PortInfo]:
    """Get established connections."""
    ports: List[PortInfo] = []
    if utils.is_linux():
        cmd = ["ss", "-tnp", "state", "established"] if utils.command_exists("ss") else ["netstat", "-tnp"]
        result = utils.run(cmd, timeout=10)
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 5:
                local = parts[4] if cmd[0] == "ss" else (parts[3] if len(parts) > 3 else "")
                remote = parts[5] if cmd[0] == "ss" and len(parts) > 5 else (parts[4] if cmd[0] == "netstat" and len(parts) > 4 else "")
                port_str = local.rsplit(":", 1)[-1] if ":" in local else "0"
                try:
                    port_num = int(port_str)
                except ValueError:
                    port_num = 0
                ports.append(
                    PortInfo(
                        port=port_num,
                        protocol="tcp",
                        state="ESTABLISHED",
                        local_addr=local,
                        remote_addr=remote,
                        pid="",
                        process="",
                    )
                )
    elif utils.is_windows():
        result = utils.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-NetTCPConnection -State Established | Select-Object LocalAddress,LocalPort,RemoteAddress,RemotePort | Format-Table -AutoSize",
            ],
            timeout=15,
        )
        lines = result.stdout.splitlines()
        if len(lines) > 3:
            for line in lines[3:]:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        port_num = int(parts[1])
                    except ValueError:
                        port_num = 0
                    ports.append(
                        PortInfo(
                            port=port_num,
                            protocol="tcp",
                            state="ESTABLISHED",
                            local_addr=f"{parts[0]}:{parts[1]}",
                            remote_addr=f"{parts[2]}:{parts[3]}" if len(parts) > 3 else "",
                            pid="",
                            process="",
                        )
                    )
    return sorted(ports, key=lambda p: p.port)


def filter_by_port(port_list: List[PortInfo], port: int) -> List[PortInfo]:
    return [p for p in port_list if p.port == port]


def check_port_open(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is open on localhost via socket.connect."""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except Exception:
        return False
