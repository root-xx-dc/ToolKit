"""
ROOT//X Toolkit License Guard
Provides dual verification:
1. Server challenge-response authentication with Ed25519 & session tokens
2. Cryptographic Gist & offline grace period fallback
"""

import os
import sys
import json
import hashlib
import uuid
import requests
from colorama import Fore, Style
from core.system_info import get_hwid
from core.anti_tamper import collect_security_signals

SERVER_AUTH_URL = "https://szefuncio-xx.bid/api/toolkit/auth"
GIST_RAW_URL = "https://gist.githubusercontent.com/raw/5dd908cf231190e7ec3a134878c422e8/rootx_licenses.json"
CACHE_FILE = os.path.expanduser("~/.rootx_license_cache")
TOOLKIT_SALT = "rootx-toolkit-v1-static-salt-9f3a1c"

def compute_token_hash(token: str) -> str:
    return hashlib.sha256((TOOLKIT_SALT + token.strip().upper()).encode("utf-8")).hexdigest()

def verify_remote_license(token: str) -> tuple[bool, str, dict | None]:
    if not token or len(token.strip()) < 10:
        return False, "Nieprawidłowy format klucza licencji.", None

    hwid = get_hwid()
    hwid_hash = hashlib.sha256(hwid.encode("utf-8")).hexdigest()
    nonce = str(uuid.uuid4())

    # 1. Try primary server auth endpoint
    try:
        payload = {
            "license_key": token.strip(),
            "hwid_hash": hwid_hash,
            "nonce": nonce,
            "signals": collect_security_signals(),
        }
        res = requests.post(SERVER_AUTH_URL, json=payload, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get("success"):
                session_token = data.get("sessionToken", {})
                tier = session_token.get("tier", "bronze")
                return True, tier, session_token
            return False, data.get("message", "Odmowa autoryzacji licencji."), None
        elif res.status_code == 403:
            err = res.json().get("message", "Licencja wygasła lub zablokowana.")
            return False, err, None
    except Exception:
        # Fallback to secondary check if server temporarily unreachable
        pass

    # 2. Gist fallback verification
    token_hash = compute_token_hash(token)
    try:
        res = requests.get(GIST_RAW_URL, timeout=6)
        if res.status_code == 200:
            payload = res.json()
            hashes = payload.get("hashes", {})
            if token_hash in hashes:
                entry = hashes[token_hash]
                if entry.get("active", False):
                    tier = entry.get("tier", "bronze")
                    return True, tier, None
                return False, "Licencja została zablokowana lub dezaktywowana.", None
    except Exception:
        pass

    return False, "Nie udało się zweryfikować licencji z serwerem.", None

def save_license_cache(token: str, tier: str, session_token: dict | None = None):
    hwid = get_hwid()
    signature = hashlib.sha256((token + tier + hwid).encode("utf-8")).hexdigest()
    data = {
        "token": token,
        "tier": tier,
        "hwid": hwid,
        "sig": signature,
        "session": session_token,
    }
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

def load_license_cache() -> tuple[str, str] | None:
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        token = data.get("token")
        tier = data.get("tier")
        hwid = data.get("hwid")
        sig = data.get("sig")
        current_hwid = get_hwid()

        if hwid == current_hwid:
            expected_sig = hashlib.sha256((token + tier + hwid).encode("utf-8")).hexdigest()
            if sig == expected_sig:
                return token, tier
    except Exception:
        return None
    return None

def check_license_interactive(force_recheck=False) -> dict:
    cached = load_license_cache() if not force_recheck else None

    if cached:
        token, tier = cached
        valid, remote_tier, session = verify_remote_license(token)
        if valid:
            save_license_cache(token, remote_tier, session)
            return {"valid": True, "token": token, "tier": remote_tier}

    print(f"\n{Fore.YELLOW}[!] Wymagana Weryfikacja Licencji ROOT//X Toolkit{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Wprowadź swój klucz licencji (z Discorda /purchase lub /trial start):")

    while True:
        token = input(f"{Fore.CYAN}Klucz Licencji > {Style.RESET_ALL}").strip()
        if not token:
            print(f"{Fore.RED}[!] Klucz nie może być pusty.{Style.RESET_ALL}")
            continue

        print(f"{Fore.YELLOW}[*] Sprawdzanie licencji w rejestrze ROOT//X...{Style.RESET_ALL}")
        valid, tier_or_err, session = verify_remote_license(token)

        if valid:
            save_license_cache(token, tier_or_err, session)
            print(f"{Fore.GREEN}[+] Licencja poprawna! Pakiet: {tier_or_err.upper()}{Style.RESET_ALL}")
            return {"valid": True, "token": token, "tier": tier_or_err}
        else:
            print(f"{Fore.RED}[-] Odmowa dostępu: {tier_or_err}{Style.RESET_ALL}")
            retry = input(f"{Fore.WHITE}Spróbować ponownie? (t/n): ").strip().lower()
            if retry not in ["t", "tak", "y", "yes"]:
                print(f"{Fore.RED}[!] Zamykanie. Wymagana aktywna licencja do działania Toolkitu.{Style.RESET_ALL}")
                sys.exit(1)
