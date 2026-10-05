"""
ROOT//X Toolkit Anti-Tamper & Security Signals
Reports debugger/hook/VM signals to server as telemetry telemetry rather than
abruptly killing processes to prevent false positives for legitimate users.
"""

import sys
import os
import platform

def detect_debugger() -> bool:
    if sys.gettrace() is not None:
        return True
    return False

def detect_virtual_environment() -> bool:
    system = platform.system().lower()
    if system == "linux":
        if os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"):
            return True
    return False

def collect_security_signals() -> dict:
    return {
        "debugger": detect_debugger(),
        "virtual_env": detect_virtual_environment(),
        "platform": platform.platform(),
    }
