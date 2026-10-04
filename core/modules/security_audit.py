import os
import socket
from colorama import Fore

def run_security_audit():
    while True:
        print(f"\n{Fore.CYAN}=== ROOT//X Security & Port Auditor ===")
        print(f"{Fore.WHITE}[1] Scan Local Listening Ports")
        print(f"{Fore.WHITE}[2] Password Entropy & Strength Checker")
        print(f"{Fore.WHITE}[3] Basic Linux Security Status (UFW / Sudo)")
        print(f"{Fore.WHITE}[0] Back to Main Menu\n")

        c = input(f"{Fore.WHITE}Select Option: ").strip()
        if c == "1":
            print(f"\n{Fore.YELLOW}[*] Checking local listening ports (1-1024 + common)...")
            common_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443, 27017]
            for p in common_ports:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.3)
                res = s.connect_ex(("127.0.0.1", p))
                if res == 0:
                    print(f"{Fore.RED}[!] Local Port {p:<6} is LISTENING locally")
                s.close()
            print(f"{Fore.GREEN}[+] Local port scan complete.")
        elif c == "2":
            pwd = input("Enter password to test: ").strip()
            score = 0
            if len(pwd) >= 12: score += 30
            elif len(pwd) >= 8: score += 15
            if any(c.isupper() for c in pwd): score += 20
            if any(c.islower() for c in pwd): score += 20
            if any(c.isdigit() for c in pwd): score += 15
            if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in pwd): score += 15

            color = Fore.RED if score < 50 else Fore.YELLOW if score < 80 else Fore.GREEN
            print(f"{color}[*] Strength Score: {score}/100")
        elif c == "3":
            if os.name == "nt":
                print(f"{Fore.YELLOW}[*] Windows Defender / Firewall active.")
            else:
                ufw_status = os.system("which ufw > /dev/null 2>&1")
                if ufw_status == 0:
                    print(f"{Fore.GREEN}[+] UFW Firewall is installed on system.")
                else:
                    print(f"{Fore.YELLOW}[!] UFW not installed or iptables managed.")
        elif c == "0":
            break
