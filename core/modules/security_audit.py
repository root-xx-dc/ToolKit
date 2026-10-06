import os
import socket
from colorama import Fore, Style

def check_local_ports():
    print(f"\n{Fore.YELLOW}[*] Scanning local listening ports (1-1024 + common services)...{Style.RESET_ALL}")
    common_ports = [
        (21, "FTP"), (22, "SSH"), (23, "Telnet"), (25, "SMTP"), (53, "DNS"),
        (80, "HTTP"), (110, "POP3"), (143, "IMAP"), (443, "HTTPS"), (445, "SMB"),
        (993, "IMAPS"), (995, "POP3S"), (3306, "MySQL"), (3389, "RDP"),
        (5432, "PostgreSQL"), (6379, "Redis"), (8080, "HTTP-Alt"), (8443, "HTTPS-Alt"),
        (27017, "MongoDB")
    ]
    open_count = 0
    for p, svc in common_ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        res = s.connect_ex(("127.0.0.1", p))
        if res == 0:
            print(f"  {Fore.RED}[!] Port {p:<6} [{svc:<10}] is ACTIVE / LISTENING locally{Style.RESET_ALL}")
            open_count += 1
        s.close()
    
    if open_count == 0:
        print(f"  {Fore.GREEN}[OK] No open standard management ports exposed locally.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}[*] Total listening services detected: {open_count}{Style.RESET_ALL}")

def test_password_strength():
    pwd = input(f"\n{Fore.WHITE}Enter password to analyze: {Style.RESET_ALL}").strip()
    if not pwd:
        return
    score = 0
    reasons = []

    if len(pwd) >= 14:
        score += 35
        reasons.append("[+] Excellent length (>= 14 chars)")
    elif len(pwd) >= 10:
        score += 20
        reasons.append("[+] Good length (>= 10 chars)")
    elif len(pwd) >= 8:
        score += 10
        reasons.append("[-] Minimal length (>= 8 chars)")
    else:
        reasons.append("[!] Too short (< 8 chars)")

    if any(c.isupper() for c in pwd):
        score += 20
        reasons.append("[+] Contains uppercase letters")
    else:
        reasons.append("[!] Missing uppercase letters")

    if any(c.islower() for c in pwd):
        score += 20
        reasons.append("[+] Contains lowercase letters")
    else:
        reasons.append("[!] Missing lowercase letters")

    if any(c.isdigit() for c in pwd):
        score += 15
        reasons.append("[+] Contains digits")
    else:
        reasons.append("[!] Missing digits")

    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in pwd):
        score += 10
        reasons.append("[+] Contains special characters")
    else:
        reasons.append("[!] Missing special characters")

    col = Fore.RED if score < 50 else (Fore.YELLOW if score < 80 else Fore.GREEN)
    rating = "WEAK" if score < 50 else ("MODERATE" if score < 80 else "STRONG / SECURE")
    
    print(f"\n{col}[#] Security Score: {score}/100 - Rating: {rating}{Style.RESET_ALL}")
    print("  Detailed Criteria:")
    for r in reasons:
        r_col = Fore.GREEN if r.startswith("[+]") else (Fore.YELLOW if r.startswith("[-]") else Fore.RED)
        print(f"    {r_col}{r}{Style.RESET_ALL}")

def check_firewall_status():
    print(f"\n{Fore.CYAN}=== System Firewall & Protection Status ==={Style.RESET_ALL}")
    if os.name == "nt":
        print(f"  {Fore.GREEN}[OK] Windows Defender Firewall subsystem active.{Style.RESET_ALL}")
    elif os.name == "posix":
        ufw_status = os.system("which ufw > /dev/null 2>&1")
        if ufw_status == 0:
            print(f"  {Fore.GREEN}[OK] UFW Firewall is installed on system.{Style.RESET_ALL}")
        else:
            iptables_status = os.system("which iptables > /dev/null 2>&1")
            if iptables_status == 0:
                print(f"  {Fore.GREEN}[OK] Iptables packet filter available.{Style.RESET_ALL}")
            else:
                print(f"  {Fore.YELLOW}[!] Standard firewall utility not detected.{Style.RESET_ALL}")

def run_security_audit():
    while True:
        print(f"\n{Fore.CYAN}=== ROOT//X Security & Port Auditor ==={Style.RESET_ALL}")
        print(f"{Fore.WHITE}[1] Scan Local Listening Ports & Services")
        print(f"{Fore.WHITE}[2] Password Entropy & Strength Checker")
        print(f"{Fore.WHITE}[3] System Firewall & Protection Status")
        print(f"{Fore.WHITE}[0] Back to Main Menu\n")

        c = input(f"{Fore.WHITE}Select Option [0-3]: {Style.RESET_ALL}").strip()
        if c == "1":
            check_local_ports()
            input(f"\n{Fore.WHITE}Press ENTER to return...{Style.RESET_ALL}")
        elif c == "2":
            test_password_strength()
            input(f"\n{Fore.WHITE}Press ENTER to return...{Style.RESET_ALL}")
        elif c == "3":
            check_firewall_status()
            input(f"\n{Fore.WHITE}Press ENTER to return...{Style.RESET_ALL}")
        elif c == "0":
            break
