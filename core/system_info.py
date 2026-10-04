import os
import platform
import uuid
import hashlib
import psutil

def get_linux_distro() -> str:
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release") as f:
                lines = f.readlines()
            for line in lines:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=")[1].strip().strip('"')
                if line.startswith("NAME="):
                    return line.split("=")[1].strip().strip('"')
        except Exception:
            pass
    return "Linux"

def get_system_summary() -> dict:
    os_type = platform.system()
    if os_type == "Linux":
        os_name = get_linux_distro()
    elif os_type == "Windows":
        os_name = f"Windows {platform.release()}"
    elif os_type == "Darwin":
        os_name = f"macOS {platform.mac_ver()[0]}"
    else:
        os_name = os_type

    cpu_count = psutil.cpu_count(logical=True)
    ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)

    return {
        "os_name": os_name,
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "cpu_cores": f"{cpu_count} Threads",
        "total_ram": f"{ram_gb} GB",
        "node_name": platform.node(),
        "hwid": get_hwid()
    }

def get_hwid() -> str:
    # Stable cross-platform hardware fingerprint
    raw = f"{platform.node()}-{platform.machine()}-{platform.processor()}-{uuid.getnode()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
