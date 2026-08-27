"""
rootx.ram_cleaner
=================
RAM / Cache Purger.

Windows: Working Set trim + Standby List purge via ctypes (requires admin)
Linux: /proc/sys/vm/drop_caches (requires sudo)
"""
from __future__ import annotations

import ctypes
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class RamInfo:
    total_mb: int
    available_mb: int
    used_mb: int
    percent: float


# ─── RAM info ─────────────────────────────────────────────────────────────────

def get_ram_info() -> RamInfo:
    try:
        import psutil
        vm = psutil.virtual_memory()
        return RamInfo(
            total_mb=vm.total // (1024 * 1024),
            available_mb=vm.available // (1024 * 1024),
            used_mb=vm.used // (1024 * 1024),
            percent=vm.percent,
        )
    except ImportError:
        pass

    system = platform.system()
    if system == "Windows":
        return _get_ram_info_windows()
    elif system == "Linux":
        return _get_ram_info_linux()
    return RamInfo(0, 0, 0, 0.0)


def _get_ram_info_windows() -> RamInfo:
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(stat)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        total = stat.ullTotalPhys // (1024 * 1024)
        avail = stat.ullAvailPhys // (1024 * 1024)
        used = total - avail
        pct = (used / total * 100) if total else 0
        return RamInfo(total_mb=total, available_mb=avail, used_mb=used, percent=round(pct, 1))
    except Exception:
        return RamInfo(0, 0, 0, 0.0)


def _get_ram_info_linux() -> RamInfo:
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    val = int(parts[1])
                    info[key] = val
        total = info.get("MemTotal", 0) // 1024
        avail = info.get("MemAvailable", 0) // 1024
        used = total - avail
        pct = (used / total * 100) if total else 0
        return RamInfo(total_mb=total, available_mb=avail, used_mb=used, percent=round(pct, 1))
    except Exception:
        return RamInfo(0, 0, 0, 0.0)


# ─── Admin check ──────────────────────────────────────────────────────────────

def is_admin() -> bool:
    try:
        if platform.system() == "Windows":
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except Exception:
        return False


# ─── Windows purge ────────────────────────────────────────────────────────────

def purge_windows_working_sets() -> bool:
    """Trim working sets of all accessible processes."""
    try:
        import psutil
        success = 0
        for proc in psutil.process_iter(["pid"]):
            try:
                handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, proc.pid)
                if handle:
                    ctypes.windll.psapi.EmptyWorkingSet(handle)
                    ctypes.windll.kernel32.CloseHandle(handle)
                    success += 1
            except Exception:
                pass
        return success > 0
    except Exception:
        return False


def purge_windows_standby() -> bool:
    """
    Purge Standby List via NtSetSystemInformation.
    Requires SeProfileSingleProcessPrivilege (Administrator).
    SystemMemoryListCommand = 4 means MemoryPurgeStandbyList.
    """
    try:
        ntdll = ctypes.windll.ntdll
        # Enable SeProfileSingleProcessPrivilege
        TOKEN_ADJUST_PRIVILEGES = 0x0020
        TOKEN_QUERY = 0x0008
        SE_PRIVILEGE_ENABLED = 0x00000002
        SE_PROF_SINGLE_PROCESS_NAME = "SeProfileSingleProcessPrivilege"

        class LUID(ctypes.Structure):
            _fields_ = [("LowPart", ctypes.c_ulong), ("HighPart", ctypes.c_long)]

        class LUID_AND_ATTRIBUTES(ctypes.Structure):
            _fields_ = [("Luid", LUID), ("Attributes", ctypes.c_ulong)]

        class TOKEN_PRIVILEGES(ctypes.Structure):
            _fields_ = [("PrivilegeCount", ctypes.c_ulong),
                         ("Privileges", LUID_AND_ATTRIBUTES * 1)]

        hToken = ctypes.c_void_p()
        ctypes.windll.advapi32.OpenProcessToken(
            ctypes.windll.kernel32.GetCurrentProcess(),
            TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
            ctypes.byref(hToken)
        )

        luid = LUID()
        ctypes.windll.advapi32.LookupPrivilegeValueW(None, SE_PROF_SINGLE_PROCESS_NAME, ctypes.byref(luid))

        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED

        ctypes.windll.advapi32.AdjustTokenPrivileges(hToken, False, ctypes.byref(tp), 0, None, None)

        # SystemMemoryListCommand = 80, MemoryPurgeStandbyList = 4
        command = ctypes.c_int(4)
        status = ntdll.NtSetSystemInformation(80, ctypes.byref(command), ctypes.sizeof(command))
        return status == 0
    except Exception:
        return False


# ─── Linux purge ──────────────────────────────────────────────────────────────

def drop_linux_caches(level: int = 3) -> bool:
    """
    Write to /proc/sys/vm/drop_caches.
    level 1 = page cache, 2 = dentries/inodes, 3 = both.
    Requires root.
    """
    try:
        with open("/proc/sys/vm/drop_caches", "w") as f:
            f.write(str(level))
        return True
    except PermissionError:
        # Try via sudo sync + echo
        try:
            subprocess.run(["sync"], check=True, timeout=5)
            subprocess.run(
                ["sudo", "sh", "-c", f"echo {level} > /proc/sys/vm/drop_caches"],
                check=True, timeout=10,
            )
            return True
        except Exception:
            return False
    except Exception:
        return False


# ─── Public API ───────────────────────────────────────────────────────────────

def clean_ram() -> Tuple[RamInfo, RamInfo, str]:
    """
    Attempt RAM cleanup. Returns (before, after, message).
    """
    before = get_ram_info()
    message = ""
    system = platform.system()

    if system == "Windows":
        if not is_admin():
            message = "Administrator privileges required for full cleanup."
        ws_ok = purge_windows_working_sets()
        sb_ok = purge_windows_standby() if is_admin() else False
        if ws_ok and sb_ok:
            message = "Working sets trimmed + Standby List purged."
        elif ws_ok:
            message = "Working sets trimmed. (Standby purge requires Admin)"
        else:
            message = "Cleanup had limited effect."
    elif system == "Linux":
        if not is_admin():
            message = "Root/sudo required for full cache drop."
        ok = drop_linux_caches(3)
        message = "Page cache + dentries + inodes dropped." if ok else "Failed to drop caches (needs sudo)."
    else:
        message = f"Platform '{system}' not supported."

    after = get_ram_info()
    return before, after, message
