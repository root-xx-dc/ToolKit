"""
ROOT//X Toolkit Obfuscation Automation Script
Uses PyArmor to protect core license and execution logic before distributing.
"""
import os
import subprocess
import sys

def run_obfuscation():
    print("[*] Installing pyarmor...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyarmor"])

    print("[*] Generating obfuscated core bundle...")
    os.makedirs("dist_obfuscated", exist_ok=True)
    subprocess.check_call([
        "pyarmor", "gen",
        "--enable-rft",
        "--output", "dist_obfuscated/core",
        "core"
    ])
    print("[+] Obfuscation complete! Safe for closed-source deployment.")

if __name__ == "__main__":
    run_obfuscation()
