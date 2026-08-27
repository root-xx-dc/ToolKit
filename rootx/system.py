"""
rootx.system
============
Collects general system information: OS/distro, kernel, architecture,
hostname, uptime, CPU, RAM, swap, GPU, motherboard/BIOS, temperature, shell.

Works on Windows, macOS and Linux. Uses `psutil` for the parts that differ
wildly between OSes (CPU/RAM/uptime/disk) and falls back to per-OS native
commands for anything psutil doesn't cover (GPU, motherboard, BIOS).

Every getter is defensive: missing files, commands or optional deps simply
produce "N/A" instead of raising.
"""

from __future__ import annotations

import os
import platform
import socket
import time
from dataclasses import dataclass
from typing import Optional

from . import utils

try:
    import psutil
except Exception:  # pragma: no cover - psutil should always be installed
    psutil = None


@dataclass
class SystemInfo:
    distro_name: str = "N/A"
    distro_id: str = "unknown"
    distro_version: str = "N/A"
    kernel: str = "N/A"
    architecture: str = "N/A"
    hostname: str = "N/A"
    user: str = "N/A"
    uptime: str = "N/A"
    shell: str = "N/A"
    cpu_model: str = "N/A"
    cpu_cores: str = "N/A"
    load_average: str = "N/A"
    ram_total: str = "N/A"
    ram_available: str = "N/A"
    swap_total: str = "N/A"
    swap_used: str = "N/A"
    gpu: str = "N/A"
    motherboard: str = "N/A"
    bios: str = "N/A"
    temperature: str = "N/A"
    disk_summary: str = "N/A"


def get_hostname() -> str:
    try:
        return socket.gethostname() or "N/A"
    except Exception:
        return "N/A"


def get_user() -> str:
    return (
        os.environ.get("USER")
        or os.environ.get("LOGNAME")
        or os.environ.get("USERNAME")
        or "N/A"
    )


def get_shell() -> str:
    if utils.is_windows():
        return os.environ.get("COMSPEC") or "cmd.exe"
    return os.environ.get("SHELL", "N/A")


def get_kernel() -> str:
    try:
        return platform.release() or "N/A"
    except Exception:
        return "N/A"


def get_uptime() -> str:
    try:
        if psutil is not None:
            seconds = time.time() - psutil.boot_time()
            return utils.human_uptime(seconds)
        if utils.is_linux():
            with open("/proc/uptime", "r") as fh:
                seconds = float(fh.readline().split()[0])
            return utils.human_uptime(seconds)
    except Exception:
        pass
    return "N/A"


def get_cpu_info() -> dict:
    model = "N/A"
    cores = "N/A"
    try:
        cores = str(os.cpu_count() or "N/A")
    except Exception:
        pass

    try:
        if utils.is_linux():
            content = utils.safe_read_file("/proc/cpuinfo")
            for line in content.splitlines():
                if line.lower().startswith("model name"):
                    model = line.split(":", 1)[1].strip()
                    break
        elif utils.is_macos():
            result = utils.run(["sysctl", "-n", "machdep.cpu.brand_string"], timeout=5)
            if result.ok and result.stdout:
                model = result.stdout.strip()
        elif utils.is_windows():
            model = platform.processor() or "N/A"
    except Exception:
        pass
    return {"model": model or "N/A", "cores": cores}


def get_load_average() -> str:
    try:
        load1, load5, load15 = os.getloadavg()
        return f"{load1:.2f}, {load5:.2f}, {load15:.2f}"
    except Exception:
        return "N/A"  # not available on Windows


def get_memory_info() -> dict:
    info = {
        "ram_total": "N/A",
        "ram_available": "N/A",
        "swap_total": "N/A",
        "swap_used": "N/A",
    }
    try:
        if psutil is not None:
            vm = psutil.virtual_memory()
            sm = psutil.swap_memory()
            info["ram_total"] = utils.human_bytes(vm.total)
            info["ram_available"] = utils.human_bytes(vm.available)
            info["swap_total"] = utils.human_bytes(sm.total)
            info["swap_used"] = utils.human_bytes(sm.used)
            return info
    except Exception:
        pass

    # Fallback: /proc/meminfo on Linux if psutil is unavailable
    if utils.is_linux():
        try:
            content = utils.safe_read_file("/proc/meminfo")
            values = {}
            for line in content.splitlines():
                if ":" not in line:
                    continue
                key, _, rest = line.partition(":")
                rest = rest.strip().split()
                if rest:
                    values[key.strip()] = int(rest[0]) * 1024
            total = values.get("MemTotal")
            available = values.get("MemAvailable")
            swap_total = values.get("SwapTotal")
            swap_free = values.get("SwapFree")
            if total is not None:
                info["ram_total"] = utils.human_bytes(total)
            if available is not None:
                info["ram_available"] = utils.human_bytes(available)
            if swap_total is not None:
                info["swap_total"] = utils.human_bytes(swap_total)
            if swap_total is not None and swap_free is not None:
                info["swap_used"] = utils.human_bytes(swap_total - swap_free)
        except Exception:
            pass
    return info


def get_gpu_info() -> str:
    try:
        if utils.is_linux():
            result = utils.run(["lspci"], check_exists=True, timeout=5)
            if result.ok and result.stdout:
                for line in result.stdout.splitlines():
                    if any(tag in line for tag in ("VGA compatible controller", "3D controller")):
                        return line.split(":", 2)[-1].strip()
        elif utils.is_macos():
            result = utils.run(
                ["system_profiler", "SPDisplaysDataType", "-detailLevel", "mini"], timeout=8
            )
            if result.ok and result.stdout:
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("Chipset Model:"):
                        return line.split(":", 1)[1].strip()
        elif utils.is_windows():
            result = utils.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_VideoController | Select-Object -First 1 -ExpandProperty Name)"],
                timeout=10,
            )
            if result.ok and result.stdout:
                return result.stdout.strip()
    except Exception:
        pass
    return "N/A"


def get_motherboard_info() -> dict:
    try:
        if utils.is_linux():
            board = utils.safe_read_file("/sys/devices/virtual/dmi/id/board_name").strip() or "N/A"
            bios = utils.safe_read_file("/sys/devices/virtual/dmi/id/bios_version").strip() or "N/A"
            return {"motherboard": board, "bios": bios}
        if utils.is_macos():
            result = utils.run(["sysctl", "-n", "hw.model"], timeout=5)
            board = result.stdout.strip() if result.ok else "N/A"
            return {"motherboard": board or "N/A", "bios": "N/A"}
        if utils.is_windows():
            board_r = utils.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_BaseBoard).Product"], timeout=10,
            )
            bios_r = utils.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_BIOS).SMBIOSBIOSVersion"], timeout=10,
            )
            board = board_r.stdout.strip() if board_r.ok and board_r.stdout else "N/A"
            bios = bios_r.stdout.strip() if bios_r.ok and bios_r.stdout else "N/A"
            return {"motherboard": board, "bios": bios}
    except Exception:
        pass
    return {"motherboard": "N/A", "bios": "N/A"}


def get_temperature() -> str:
    try:
        if psutil is not None and hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures() or {}
            for entries in temps.values():
                for entry in entries:
                    if entry.current:
                        return f"{entry.current:.1f} C"
    except Exception:
        pass

    # Linux thermal zone fallback
    if utils.is_linux():
        base = "/sys/class/thermal"
        try:
            if os.path.isdir(base):
                for entry in sorted(os.listdir(base)):
                    if not entry.startswith("thermal_zone"):
                        continue
                    temp_path = os.path.join(base, entry, "temp")
                    raw = utils.safe_read_file(temp_path).strip()
                    if raw.isdigit():
                        celsius = int(raw) / 1000.0
                        return f"{celsius:.1f} C"
        except Exception:
            pass
    return "N/A"  # sensor access on macOS/Windows requires vendor tools we don't bundle


def get_disk_summary() -> str:
    try:
        if psutil is not None:
            root = "C:\\" if utils.is_windows() else "/"
            usage = psutil.disk_usage(root)
            return f"{utils.human_bytes(usage.used)} used / {utils.human_bytes(usage.total)} total ({usage.percent:.0f}%)"
    except Exception:
        pass
    return "N/A"


def collect() -> SystemInfo:
    """Collect all system information into a single SystemInfo object."""
    distro = utils.detect_distro()
    cpu = get_cpu_info()
    mem = get_memory_info()
    board = get_motherboard_info()

    return SystemInfo(
        distro_name=distro["name"],
        distro_id=distro["id"],
        distro_version=distro["version"] or "N/A",
        kernel=get_kernel(),
        architecture=utils.detect_architecture(),
        hostname=get_hostname(),
        user=get_user(),
        uptime=get_uptime(),
        shell=get_shell(),
        cpu_model=cpu["model"],
        cpu_cores=cpu["cores"],
        load_average=get_load_average(),
        ram_total=mem["ram_total"],
        ram_available=mem["ram_available"],
        swap_total=mem["swap_total"],
        swap_used=mem["swap_used"],
        gpu=get_gpu_info(),
        motherboard=board["motherboard"],
        bios=board["bios"],
        temperature=get_temperature(),
        disk_summary=get_disk_summary(),
    )
