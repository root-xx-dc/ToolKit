"""
ROOT//X Toolkit Opt-In Telemetry Client
Strictly opt-in error tracking. Sanitizes all local user paths before sending.
"""

import os
import sys
import platform
import json
import re
import requests

TELEMETRY_ENDPOINT = "https://szefuncio-xx.bid/api/telemetry"
PREF_FILE = os.path.expanduser("~/.rootx_telemetry_pref")

def is_telemetry_enabled() -> bool:
    if not os.path.exists(PREF_FILE):
        return False
    try:
        with open(PREF_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("enabled", False)
    except Exception:
        return False

def prompt_telemetry_consent():
    if os.path.exists(PREF_FILE):
        return

    print("\n" + "=" * 55)
    print("ROOT//X Toolkit Telemetria & Raportowanie Błędów")
    print("=" * 55)
    print("Czy wyrażasz zgodę na wysyłanie anonimowych kodów błędów")
    print("w celu poprawy stabilności aplikacji? (Domyślnie: NIE)")
    print("Nie są zbierane żadne dane osobowe ani zawartość plików.")
    
    choice = input("Włącz telemetrię opt-in? (t/N): ").strip().lower()
    enabled = choice in ["t", "tak", "y", "yes"]

    try:
        with open(PREF_FILE, "w", encoding="utf-8") as f:
            json.dump({"enabled": enabled}, f)
    except Exception:
        pass

def sanitize_stack_trace(stack: str) -> str:
    if not stack:
        return ""
    # Redact user names and personal home directories
    redacted = re.sub(r"(/Users/[^/]+|/home/[^/]+|C:\\Users\\[^\\]+)", "[REDACTED_USER_PATH]", stack)
    return redacted[:3500]

def send_error_report(version: str, error_code: str, stack_trace: str = ""):
    if not is_telemetry_enabled():
        return

    try:
        payload = {
            "version": version,
            "os_name": f"{platform.system()} {platform.release()}",
            "error_code": error_code,
            "sanitized_stack": sanitize_stack_trace(stack_trace),
        }
        requests.post(TELEMETRY_ENDPOINT, json=payload, timeout=3)
    except Exception:
        pass
