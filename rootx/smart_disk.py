"""
rootx.smart_disk
================
Disk Health & S.M.A.R.T. Monitor.

Windows: PowerShell Get-PhysicalDisk + Get-StorageReliabilityCounter
Linux:   smartctl (smartmontools package)
"""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DiskHealth:
    device: str
    model: str
    health: str               # PASSED / FAILED / UNKNOWN
    temperature_c: Optional[int]
    reallocated_sectors: Optional[int]
    power_on_hours: Optional[int]
    tbw_tb: Optional[float]
    size_gb: Optional[float]
    interface: str            # SSD / HDD / NVMe / Unknown


def _run(cmd: List[str], encoding: str = "utf-8") -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding=encoding, errors="replace", timeout=20)
        return r.stdout or ""
    except Exception:
        return ""


# ─── Linux ────────────────────────────────────────────────────────────────────

def is_smartctl_available() -> bool:
    return bool(_run(["smartctl", "--version"]))


def _get_linux_block_devices() -> List[str]:
    devices = []
    block = "/sys/block"
    try:
        for name in os.listdir(block):
            # Skip loop, ram, dm devices
            if name.startswith(("loop", "ram", "dm", "sr", "fd")):
                continue
            devices.append(f"/dev/{name}")
    except Exception:
        pass
    return devices


def _parse_smartctl_output(output: str, device: str) -> DiskHealth:
    health = "UNKNOWN"
    model = "Unknown"
    temp: Optional[int] = None
    realloc: Optional[int] = None
    hours: Optional[int] = None
    tbw: Optional[float] = None
    size: Optional[float] = None
    interface = "Unknown"

    for line in output.splitlines():
        line_stripped = line.strip()
        low = line_stripped.lower()

        if "overall-health self-assessment test result" in low or "smart overall-health" in low:
            if "passed" in low:
                health = "PASSED"
            elif "failed" in low:
                health = "FAILED"
        elif line_stripped.startswith("Device Model:") or line_stripped.startswith("Model Number:"):
            model = line_stripped.split(":", 1)[-1].strip()
        elif "Rotation Rate" in line_stripped:
            if "Solid State" in line_stripped:
                interface = "SSD"
            else:
                interface = "HDD"
        elif "NVMe Version" in line_stripped or "nvme" in device.lower():
            interface = "NVMe"
        elif "Temperature_Celsius" in line_stripped or "Temperature:" in line_stripped:
            m = re.search(r"(\d+)\s*$", line_stripped)
            if m:
                try:
                    temp = int(m.group(1))
                except ValueError:
                    pass
        elif "Reallocated_Sector_Ct" in line_stripped:
            m = re.search(r"\s(\d+)\s*$", line_stripped)
            if m:
                try:
                    realloc = int(m.group(1))
                except ValueError:
                    pass
        elif "Power_On_Hours" in line_stripped:
            m = re.search(r"\s(\d+)\s*$", line_stripped)
            if m:
                try:
                    hours = int(m.group(1))
                except ValueError:
                    pass
        elif "Total_LBAs_Written" in line_stripped:
            m = re.search(r"\s(\d+)\s*$", line_stripped)
            if m:
                try:
                    lba = int(m.group(1))
                    tbw = round(lba * 512 / (1024 ** 4), 2)
                except ValueError:
                    pass
        elif "User Capacity" in line_stripped:
            m = re.search(r"[\d,]+", line_stripped.replace(",", ""))
            if m:
                try:
                    size = round(int(m.group().replace(",", "")) / (1024 ** 3), 1)
                except ValueError:
                    pass

    return DiskHealth(
        device=device,
        model=model,
        health=health,
        temperature_c=temp,
        reallocated_sectors=realloc,
        power_on_hours=hours,
        tbw_tb=tbw,
        size_gb=size,
        interface=interface,
    )


def get_linux_disk_health() -> List[DiskHealth]:
    results = []
    devices = _get_linux_block_devices()
    for dev in devices:
        output = _run(["smartctl", "-A", "-H", "-i", dev])
        if output:
            results.append(_parse_smartctl_output(output, dev))
    return results


# ─── Windows ──────────────────────────────────────────────────────────────────

_PS_SCRIPT = r"""
$disks = Get-PhysicalDisk
$result = foreach ($d in $disks) {
    $rel = $d | Get-StorageReliabilityCounter -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        DeviceId            = $d.DeviceId
        FriendlyName        = $d.FriendlyName
        MediaType           = $d.MediaType
        HealthStatus        = $d.HealthStatus
        Size                = $d.Size
        Temperature         = $rel.Temperature
        PowerOnHours        = $rel.PowerOnHours
        ReadErrorsTotal     = $rel.ReadErrorsTotal
        WriteErrorsTotal    = $rel.WriteErrorsTotal
    }
}
$result | ConvertTo-Json -Depth 3
"""


def get_windows_disk_health() -> List[DiskHealth]:
    output = _run([
        "powershell", "-NoProfile", "-NonInteractive",
        "-Command", _PS_SCRIPT,
    ])
    results = []
    try:
        data = json.loads(output)
        if isinstance(data, dict):
            data = [data]
        for d in data:
            size = d.get("Size")
            size_gb = round(int(size) / (1024 ** 3), 1) if size else None
            temp = d.get("Temperature")
            temp_c = int(temp) if temp is not None else None
            hours = d.get("PowerOnHours")
            poh = int(hours) if hours is not None else None
            health_raw = str(d.get("HealthStatus", "Unknown"))
            if "healthy" in health_raw.lower():
                health = "PASSED"
            elif "unhealthy" in health_raw.lower() or "warning" in health_raw.lower():
                health = "FAILED"
            else:
                health = "UNKNOWN"
            media = str(d.get("MediaType", ""))
            if "SSD" in media or "Solid" in media:
                interface = "SSD"
            elif "NVMe" in media:
                interface = "NVMe"
            elif "HDD" in media or "Unspecified" in media:
                interface = "HDD"
            else:
                interface = media or "Unknown"

            results.append(DiskHealth(
                device=f"Disk {d.get('DeviceId', '?')}",
                model=str(d.get("FriendlyName", "Unknown")),
                health=health,
                temperature_c=temp_c,
                reallocated_sectors=None,
                power_on_hours=poh,
                tbw_tb=None,
                size_gb=size_gb,
                interface=interface,
            ))
    except (json.JSONDecodeError, TypeError, KeyError):
        pass
    return results


# ─── Public API ───────────────────────────────────────────────────────────────

def get_all_disk_health() -> List[DiskHealth]:
    system = platform.system()
    if system == "Linux":
        return get_linux_disk_health()
    elif system == "Windows":
        return get_windows_disk_health()
    return []
