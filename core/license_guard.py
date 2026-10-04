import os
import sys
import json
import hashlib
import hmac
import requests
from colorama import Fore, Style
from core.system_info import get_hwid

TOOLKIT_SALT = "rootx-toolkit-v1-static-salt-9f3a1c"
GIST_RAW_URL = "https://gist.githubusercontent.com/raw/5dd908cf231190e7ec3a134878c422e8/rootx_licenses.json"
CACHE_FILE = os.path.expanduser("~/.rootx_license_cache")

def compute_token_hash(token: str) -> str:
    return hashlib.sha256((TOOLKIT_SALT + token.strip().upper()).encode("utf-8")).hexdigest()

def verify_remote_license(token: str) -> tuple[bool, str]:
    if not token or len(token.strip()) < 16:
        return False, "Invalid token length"

    token_hash = compute_token_hash(token)

    try:
        res = requests.get(GIST_RAW_URL, timeout=6)
        if res.status_code != 200:
            return False, "Failed to connect to ROOT//X License Authority."

        payload = res.json()
        hashes = payload.get("hashes", {})

        if token_hash in hashes:
            entry = hashes[token_hash]
            if entry.get("active", False):
                tier = entry.get("tier", "bronze")
                return True, tier
            return False, "Your license has been suspended or deactivated."

        return False, "License token not found in registry."
    except Exception as e:
        return False, f"Verification error: {str(e)}"

def save_license_cache(token: str, tier: str):
    hwid = get_hwid()
    # Sign cache with HWID
    signature = hashlib.sha256((token + tier + hwid).encode("utf-8")).hexdigest()
    data = {
        "token": token,
        "tier": tier,
        "hwid": hwid,
        "sig": signature
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
        # Quick background verification
        valid, remote_tier = verify_remote_license(token)
        if valid:
            return {"valid": True, "token": token, "tier": remote_tier}

    print(f"\n{Fore.YELLOW}[!] ROOT//X License Verification Required{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Please enter your product activation key (received from Discord /key_add or purchase):")

    while True:
        token = input(f"{Fore.CYAN}License Key > {Style.RESET_ALL}").strip()
        if not token:
            print(f"{Fore.RED}[!] Key cannot be empty.")
            continue

        print(f"{Fore.YELLOW}[*] Validating with ROOT//X License Authority...{Style.RESET_ALL}")
        valid, tier_or_err = verify_remote_license(token)

        if valid:
            save_license_cache(token, tier_or_err)
            print(f"{Fore.GREEN}[+] License verified successfully! Tier: {tier_or_err.upper()}{Style.RESET_ALL}")
            return {"valid": True, "token": token, "tier": tier_or_err}
        else:
            print(f"{Fore.RED}[-] Access Denied: {tier_or_err}{Style.RESET_ALL}")
            retry = input(f"{Fore.WHITE}Try again? (y/n): ").strip().lower()
            if retry != "y":
                print(f"{Fore.RED}[!] Terminating. Valid license required to execute ROOT//X Toolkit.")
                sys.exit(1)
