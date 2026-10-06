import os
import sys
import time
import platform
from colorama import init, Fore, Style
from core.license_guard import check_license_interactive
from core.presence import DiscordRPC
from core.system_info import get_system_summary
from core.modules.server_manager import run_server_manager
from core.modules.network_tools import run_network_tools
from core.modules.security_audit import run_security_audit

init(autoreset=True)

VERSION = "2.4.0-PRO"
APPLICATION_ID = "1556241281733107733"

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def print_banner(tier="Active", distro="Unknown"):
    clear_screen()
    banner = f"""
{Fore.CYAN}██████╗  ██████╗  ██████╗ ████████╗{Fore.MAGENTA}██╗  ██╗
{Fore.CYAN}██╔══██╗██╔═══██╗██╔═══██╗╚══██╔══╝{Fore.MAGENTA}╚██╗██╔╝
{Fore.CYAN}██████╔╝██║   ██║██║   ██║   ██║   {Fore.MAGENTA} ╚███╔╝ 
{Fore.CYAN}██╔══██╗██║   ██║██║   ██║   ██║   {Fore.MAGENTA} ██╔██╗ 
{Fore.CYAN}██║  ██║╚██████╔╝╚██████╔╝   ██║   {Fore.MAGENTA}██╔╝ ██╗
{Fore.CYAN}╚═╝  ╚═╝ ╚═════╝  ╚═════╝    ╚═╝   {Fore.MAGENTA}╚═╝  ╚═╝{Style.RESET_ALL}
{Fore.WHITE}       ROOT//X Advanced System & Network Toolkit
{Fore.WHITE}       Version: {Fore.GREEN}{VERSION}{Fore.WHITE} | OS: {Fore.YELLOW}{distro}{Fore.WHITE} | Tier: {Fore.MAGENTA}{tier}
{Fore.CYAN}=============================================================
"""
    print(banner)

def run_toolkit():
    # 1. Hardware & OS detection
    sys_info = get_system_summary()
    distro_name = sys_info.get("os_name", platform.system())

    print(f"{Fore.CYAN}[*] Initializing ROOT//X Toolkit on {distro_name}...")

    # 2. Cryptographic License Verification
    license_data = check_license_interactive()
    tier = license_data.get("tier", "STANDARD").upper()

    # 3. Start Discord Rich Presence
    rpc = DiscordRPC(client_id=APPLICATION_ID)
    rpc.start(tier=tier, distro=distro_name)

    while True:
        print_banner(tier=tier, distro=distro_name)
        print(f"{Fore.WHITE}[1] {Fore.CYAN}Server & Process Management")
        print(f"{Fore.WHITE}[2] {Fore.CYAN}Network & Diagnostics Suite")
        print(f"{Fore.WHITE}[3] {Fore.CYAN}Security & Port Auditor")
        print(f"{Fore.WHITE}[4] {Fore.CYAN}System Information & HWID")
        print(f"{Fore.WHITE}[5] {Fore.CYAN}Refresh License Status")
        print(f"{Fore.WHITE}[0] {Fore.RED}Exit Toolkit\n")

        choice = input(f"{Fore.WHITE}Select Option [0-5]: {Style.RESET_ALL}").strip()

        if choice == "1":
            rpc.update_status(details="Server & Process Manager", state=f"Tier: {tier}")
            run_server_manager()
        elif choice == "2":
            rpc.update_status(details="Network Diagnostics Suite", state=f"Tier: {tier}")
            run_network_tools()
        elif choice == "3":
            rpc.update_status(details="Security & Audit Tools", state=f"Tier: {tier}")
            run_security_audit()
        elif choice == "4":
            print_banner(tier=tier, distro=distro_name)
            print(f"{Fore.GREEN}=== System & Hardware Fingerprint ===")
            for k, v in sys_info.items():
                print(f"{Fore.WHITE}{k.replace('_', ' ').title()}: {Fore.CYAN}{v}")
            input(f"\n{Fore.WHITE}Press ENTER to return to menu...")
        elif choice == "5":
            license_data = check_license_interactive(force_recheck=True)
            tier = license_data.get("tier", "STANDARD").upper()
        elif choice == "0":
            print(f"\n{Fore.YELLOW}[*] Shutting down ROOT//X Toolkit...")
            rpc.stop()
            time.sleep(0.5)
            sys.exit(0)
        else:
            print(f"{Fore.RED}[!] Invalid selection.")
            time.sleep(1)

def main():
    try:
        run_toolkit()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()
